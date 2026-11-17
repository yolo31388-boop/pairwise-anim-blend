"""Character animation blend tree and state machine.

Implemented fixes:
- 1D blend weights are clamped to the threshold range and normalized so the
  weights always sum to one, even when the parameter runs past the last clip.
- Pose blending handles scalar tracks and nested bone tracks, always producing
  fresh containers (the caller never aliases the input poses).
- Root motion keeps only the horizontal (X/Z) displacement; vertical (Y) drift
  is dropped so the character does not float on slopes.
- Phase synchronization blends across the cycle boundary by taking the short
  way around the unit phase circle.
- Footstep events fired twice during one transition are deduplicated by name,
  keeping the latest timestamp while preserving first-seen order.
"""


def _smoothstep(value):
    """Hermite smoothstep clamped to [0, 1] (zero slope at both ends)."""
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def normalize_weights(param, entries):
    """Return per-entry blend weights for a 1D blend tree.

    Entries may arrive in any order; they are sorted by threshold internally
    while weights are returned in the caller's original order. Inside the
    threshold range the two surrounding clips are blended linearly. Past the
    outer thresholds the endpoint clip is selected; with three or more clips
    the influence hands off to the last two clips through a smooth, bounded
    curve instead of hard-snapping, which is what made the whole leg teleport
    when the walk -> run transition crossed the boundary.
    """
    if not entries:
        return []

    order = sorted(range(len(entries)),
                   key=lambda i: entries[i]["threshold"])
    thresholds = [entries[i]["threshold"] for i in order]
    count = len(thresholds)
    sorted_weights = [0.0] * count

    if count == 1:
        sorted_weights[0] = 1.0
    elif param <= thresholds[0]:
        sorted_weights[0] = 1.0
    elif param >= thresholds[-1]:
        if count == 2:
            # Two clips: clamp to the endpoint clip.
            sorted_weights[-1] = 1.0
        else:
            # Ease the second-to-last clip back in over one local gap of
            # overshoot. The share starts at zero on the boundary (so the
            # handoff is continuous), is capped at 2/3 (the nearest clip always
            # stays dominant and the weights never drift, however far the
            # parameter runs), and the pair always sums back to one. Degenerate
            # thresholds (zero-width last gap) fall back to a hard clamp.
            local_gap = thresholds[-1] - thresholds[-2]
            if local_gap <= 0.0:
                sorted_weights[-1] = 1.0
            else:
                overshoot = param - thresholds[-1]
                far_share = (2.0 / 3.0) * _smoothstep(overshoot / local_gap)
                sorted_weights[-1] = 1.0 - far_share
                sorted_weights[-2] = far_share
    else:
        for i in range(count - 1):
            low, high = thresholds[i], thresholds[i + 1]
            if low <= param < high:
                alpha = (param - low) / (high - low)
                sorted_weights[i] = 1.0 - alpha
                sorted_weights[i + 1] = alpha
                break

    weights = [0.0] * count
    for position, original_index in enumerate(order):
        weights[original_index] = sorted_weights[position]
    return weights


def _weighted_blend(samples):
    """Blend ``(value, weight)`` pairs, recursing into nested containers.

    Scalars collapse to a weighted sum; dicts and lists/tuples are rebuilt as
    fresh containers so the result never aliases any input pose.
    """
    first = samples[0][0]
    if isinstance(first, dict):
        return {
            key: _weighted_blend(
                [(value[key], weight) for value, weight in samples])
            for key in first
        }
    if isinstance(first, (list, tuple)):
        return [
            _weighted_blend([(value[i], weight) for value, weight in samples])
            for i in range(len(first))
        ]
    return sum(value * weight for value, weight in samples)


def blend_poses(entries, param):
    """Blend every entry's pose by its normalized 1D blend weight.

    Scalar tracks and arbitrarily nested bone tracks are both supported. The
    returned pose is rebuilt as fresh containers, so it never aliases the input
    poses and can be safely mutated by the caller.
    """
    if not entries:
        return {}
    weights = normalize_weights(param, entries)
    samples = [(entry["pose"], weight)
               for entry, weight in zip(entries, weights)]
    return _weighted_blend(samples)


def extract_root_motion(pose):
    """Extract horizontal root motion, dropping the vertical (Y) component."""
    if "root" not in pose:
        return [0.0, 0.0, 0.0]
    root = pose["root"]
    return [float(root[0]), 0.0, float(root[2])]


def sync_phase(first, second, alpha):
    """Blend two normalized [0, 1) phases along the short arc of the cycle."""
    delta = second - first
    # Take the short way across the 0/1 wrap boundary.
    if delta > 0.5:
        second -= 1.0
    elif delta < -0.5:
        second += 1.0
    blended = first + (second - first) * alpha
    return blended % 1.0


def dedupe_events(events):
    """Collapse repeated events (same name) keeping the latest timestamp.

    Distinct event names keep their first-seen order so the event track stays
    deterministic across loop boundaries and transitions.
    """
    latest = {}
    order = []
    for event in events:
        name = event["name"]
        if name not in latest:
            latest[name] = dict(event)
            order.append(name)
        elif event["t"] >= latest[name]["t"]:
            latest[name] = dict(event)
    return [latest[name] for name in order]
