"""Release gates for newly introduced errors, even when average quality improves."""

from pathlib import Path

from .data import fingerprint, load_samples, read_jsonl
from .gate import finite_number, gate_service
from .metrics import compare
from .provenance import validate_manifests


def gate_regressions(dataset, reference, candidate, constraints):
    """Validate saved service evidence, then gate observed paired task regressions.

    Thresholds concern observed quality only. Bootstrap intervals are descriptive,
    not a noninferiority guarantee, and service budgets use the separate gate API.
    """
    allowed = {'max_task_regressions', 'max_task_loss_pp', 'min_source_groups'}
    if not isinstance(constraints, dict) or set(constraints) - allowed:
        raise ValueError('Unknown regression constraints')
    limits = constraints.get('max_task_regressions')
    if not isinstance(limits, dict) or not limits:
        raise ValueError('Specify max_task_regressions for required tasks')
    if any(not isinstance(task, str) or not task or type(limit) is not int or limit < 0
           for task, limit in limits.items()):
        raise ValueError('Regression counts must be nonnegative integers for named tasks')
    losses = constraints.get('max_task_loss_pp', {})
    if not isinstance(losses, dict) or set(losses) - limits.keys() or any(
            not finite_number(value) or value > 100 for value in losses.values()):
        raise ValueError('Loss margins must be finite percentage points from 0 to 100 for required tasks')
    minimum = constraints.get('min_source_groups', 1)
    if type(minimum) is not int or minimum < 1:
        raise ValueError('min_source_groups must be a positive integer')
    reference, candidate = Path(reference), Path(candidate)
    # Both runs must be genuine, internally consistent service evidence before pairing.
    validation = {'min_task_em': {task: 0 for task in limits}}
    gate_service(dataset, reference, validation)
    gate_service(dataset, candidate, validation)
    ref = read_jsonl(reference / 'predictions.jsonl')
    cand = read_jsonl(candidate / 'predictions.jsonl')
    ids = {record['id'] for record in ref}
    rows = [row for row in load_samples(dataset) if row['id'] in ids]
    digest = fingerprint(rows, dataset)
    provenance = validate_manifests(reference / 'predictions.jsonl', candidate / 'predictions.jsonl',
                                    dataset_sha256=digest)
    comparison = compare(rows, ref, cand)
    checks = []
    for task, limit in sorted(limits.items()):
        summary = comparison['tasks'].get(task)
        regressions = summary['regressions'] if summary else None
        checks.append({'metric': f'{task}.regressions', 'observed': regressions,
                       'target': limit, 'passed': regressions is not None and regressions <= limit})
        groups = summary['independent_groups'] if summary else 0
        checks.append({'metric': f'{task}.source_groups', 'observed': groups,
                       'target': minimum, 'passed': groups >= minimum})
        if task in losses:
            loss = -summary['delta_pp'] if summary else None
            checks.append({'metric': f'{task}.loss_pp', 'observed': loss,
                           'target': losses[task], 'passed': loss is not None and loss <= losses[task]})
    return {
        'accepted': all(check['passed'] for check in checks), 'checks': checks,
        'tasks': comparison['tasks'], 'regressions': comparison['failures'],
        'requests': len(rows), 'dataset_sha256': digest,
        'provenance': provenance, 'bootstrap': comparison['bootstrap'],
        'unconstrained_tasks': sorted(set(comparison['tasks']) - limits.keys()),
        'evidence_scope': 'Observed paired service quality; intervals are descriptive, not a guarantee. '
                          'Client requests are verified; server tensors and weight identity are not attested.',
    }
