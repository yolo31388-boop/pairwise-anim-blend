import pytest

from animation.blend import (
    blend_poses,
    dedupe_events,
    extract_root_motion,
    normalize_weights,
    sync_phase,
)


def entries():
    return [
        {"threshold": 0.0, "pose": {"x": 0.0}},
        {"threshold": 1.0, "pose": {"x": 10.0}},
    ]


def test_normalize_below_first_threshold():
    assert normalize_weights(-1.0, entries()) == pytest.approx([1.0, 0.0])


def test_normalize_above_last_threshold():
    assert normalize_weights(2.0, entries()) == pytest.approx([0.0, 1.0])


def test_normalize_middle_weights_sum_to_one():
    weights = normalize_weights(0.5, entries())
    assert weights == pytest.approx([0.5, 0.5])


def test_normalize_exact_threshold_is_exclusive():
    assert normalize_weights(1.0, entries()) == pytest.approx([0.0, 1.0])


def test_normalize_three_entries_is_monotonic():
    result = normalize_weights(
        0.64,
        [
            {"threshold": 0.0, "pose": {}},
            {"threshold": 0.5, "pose": {}},
            {"threshold": 0.2, "pose": {}},
        ],
    )
    assert result == pytest.approx([0.0, 0.7, 0.3], rel=1e-2)


def test_blend_scalar_pose():
    result = blend_poses(entries(), 0.3)
    assert result["x"] == pytest.approx(3.0)


def test_blend_nested_pose_is_not_shared():
    result = blend_poses(
        [{"threshold": 0.0, "pose": {"bone": [0.0, 0.0]}},
         {"threshold": 1.0, "pose": {"bone": [10.0, 20.0]}}],
        0.5,
    )
    assert result["bone"] == pytest.approx([5.0, 10.0])


def test_root_motion_drops_vertical_component():
    assert extract_root_motion({"root": [1.0, 2.0, 3.0]}) == pytest.approx([1.0, 0.0, 3.0])


def test_root_motion_missing_returns_zero_vector():
    assert extract_root_motion({}) == pytest.approx([0.0, 0.0, 0.0])


def test_sync_phase_wraps_across_boundary():
    assert sync_phase(0.9, 0.1, 0.5) == pytest.approx(0.0)


def test_sync_phase_blends_in_middle():
    assert sync_phase(0.2, 0.4, 0.5) == pytest.approx(0.3)


def test_sync_phase_alpha_zero_returns_first():
    assert sync_phase(0.2, 0.4, 0.0) == pytest.approx(0.2)


def test_sync_phase_alpha_one_returns_second():
    assert sync_phase(0.2, 0.4, 1.0) == pytest.approx(0.4)


def test_dedupe_events_collapses_same_name():
    events = [{"name": "footstep", "t": 0.0}, {"name": "footstep", "t": 1.0}]
    result = dedupe_events(events)
    assert len(result) == 1
    assert result[0]["t"] == pytest.approx(1.0)


def test_dedupe_events_keeps_distinct_names():
    events = [{"name": "a", "t": 0.0}, {"name": "b", "t": 1.0}]
    result = dedupe_events(events)
    assert [event["name"] for event in result] == ["a", "b"]
