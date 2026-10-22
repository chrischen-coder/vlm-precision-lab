"""Saved synthetic service records exercise release decisions, not GPU performance."""
import json
from pathlib import Path

from PIL import Image
import pytest

from precisionlab.data import read_jsonl, write_jsonl
from precisionlab.metrics import compare
from precisionlab.regression import gate_regressions
from precisionlab.serving import evaluate_service


@pytest.fixture
def runs(tmp_path, monkeypatch):
    Image.new('RGB', (4, 4), 'white').save(tmp_path / 'image.png')
    rows = [{'id': str(i), 'group_id': str(i), 'image': 'image.png', 'split': 'dev',
             'task': 'amount', 'prompt': str(i), 'answer': '10.00', 'features': []} for i in range(3)]
    dataset = tmp_path / 'samples.jsonl'
    write_jsonl(dataset, rows)
    wrong = {'reference': '1', 'candidate': '0'}

    def stream(url, body, **kwargs):
        prompt = body['messages'][0]['content'][1]['text']
        return {'prediction': '99.00' if prompt == wrong[body['model']] else '10.00',
                'latency_seconds': .2, 'ttft_seconds': .1, 'finish_reason': 'stop'}

    monkeypatch.setattr('precisionlab.serving.stream_prediction', stream)
    for name in wrong:
        evaluate_service(dataset, tmp_path / name, endpoint='http://fixture.invalid/v1',
                         model=name, base_revision='fixture', warmup=0)
    return dataset, tmp_path / 'reference', tmp_path / 'candidate'


def test_equal_aggregate_score_cannot_hide_new_critical_error(runs):
    result = gate_regressions(*runs, {'max_task_regressions': {'amount': 0}})
    assert not result['accepted']
    assert result['tasks']['amount']['delta_pp'] == 0
    assert result['tasks']['amount']['recoveries'] == 1
    assert [row['id'] for row in result['regressions']] == ['0']
    assert [c['metric'] for c in result['checks'] if not c['passed']] == ['amount.regressions']
    assert result['provenance']['manifests_verified']


def test_explicit_tolerance_and_source_group_gate(runs):
    assert gate_regressions(*runs, {'max_task_regressions': {'amount': 1},
                                  'max_task_loss_pp': {'amount': 0}})['accepted']
    result = gate_regressions(*runs, {'max_task_regressions': {'amount': 1}, 'min_source_groups': 30})
    assert not result['accepted']
    assert [c['metric'] for c in result['checks'] if not c['passed']] == ['amount.source_groups']


def test_missing_required_task_fails_closed(runs):
    result = gate_regressions(*runs, {'max_task_regressions': {'missing': 0}})
    assert not result['accepted']
    assert result['checks'][0]['observed'] is None


def test_edited_predictions_and_changed_decoding_are_rejected(runs):
    dataset, reference, candidate = runs
    manifest_file = candidate / 'manifest.json'
    manifest = json.loads(manifest_file.read_text())
    manifest['controls']['decode']['max_tokens'] = 8
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='request no longer matches'):
        gate_regressions(*runs, {'max_task_regressions': {'amount': 0}})
    manifest['controls']['decode']['max_tokens'] = 32
    manifest_file.write_text(json.dumps(manifest))
    records = read_jsonl(candidate / 'predictions.jsonl')
    records[0]['prediction'] = '10.00'
    write_jsonl(candidate / 'predictions.jsonl', records)
    with pytest.raises(ValueError, match='predictions changed'):
        gate_regressions(*runs, {'max_task_regressions': {'amount': 0}})


def test_failed_request_cannot_match_correct_residual_text():
    rows = [{'id': 'one', 'group_id': 'one', 'task': 'amount', 'answer': '10',
             'image': 'a.png', 'prompt': 'Read'}]
    reference = [{'id': 'one', 'input_sha256': 'same', 'prediction': '10', 'success': True}]
    candidate = [{**reference[0], 'success': False}]
    result = compare(rows, reference, candidate, repetitions=100)
    assert result['overall']['candidate_em'] == 0
    assert result['semantic_tasks']['amount']['candidate_em'] == 0
    assert result['overall']['regressions'] == 1
    candidate[0]['success'] = 'false'
    with pytest.raises(ValueError, match='booleans'):
        compare(rows, reference, candidate)


def test_bad_thresholds_rejected_before_loading_runs():
    for constraint in [{}, {'max_task_regressions': {'amount': True}},
                       {'max_task_regressions': {'amount': -1}},
                       {'max_task_regressions': {'amount': 0}, 'max_task_loss_pp': {'amount': float('nan')}},
                       {'max_task_regressions': {'amount': 0}, 'min_source_groups': 0},
                       {'max_task_regressions': {'amount': 0}, 'unknown': 1}]:
        with pytest.raises(ValueError):
            gate_regressions('absent', 'absent', 'absent', constraint)


def test_cli_reject_exit_and_exclusive_output(runs, tmp_path, monkeypatch):
    from precisionlab.cli import main
    dataset, reference, candidate = runs
    constraints = tmp_path / 'limits.json'
    constraints.write_text(json.dumps({'max_task_regressions': {'amount': 0}}))
    output = tmp_path / 'decision.json'
    monkeypatch.setattr('sys.argv', ['precisionlab', 'regression-gate', '--dataset', str(dataset),
        '--reference', str(reference), '--candidate', str(candidate), '--constraints', str(constraints),
        '--output', str(output)])
    with pytest.raises(SystemExit) as raised:
        main()
    assert raised.value.code == 2
    assert not json.loads(output.read_text())['accepted']
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        main()
    assert output.read_bytes() == before
