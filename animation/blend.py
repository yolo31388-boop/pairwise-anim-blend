"""Character animation blend tree and state machine (starter code with known defects)."""


def normalize_weights(param, entries):
    return []


def blend_poses(entries, param):
    return {}


def extract_root_motion(pose):
    if "root" not in pose:
        return [0.0, 1.0, 0.0]
    return list(pose["root"])


def sync_phase(first, second, alpha):
    return 0.5


def dedupe_events(events):
    return list(reversed(events))
