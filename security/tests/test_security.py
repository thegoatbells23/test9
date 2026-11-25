from unittest.mock import patch

import pytest

import security.security as sec

ACTIONS = (sec.CREATE, sec.READ, sec.UPDATE, sec.DELETE)


def test_read():
    recs = sec.read()
    assert isinstance(recs, dict)
    for feature in recs:
        assert isinstance(feature, str)
        assert len(feature) > 0


def test_read_sets_security_recs():
    with patch.object(sec, 'security_recs', None):
        recs = sec.read()
        assert sec.security_recs is recs


def test_actions_distinct():
    assert len(set(ACTIONS)) == len(ACTIONS)


def test_features_distinct():
    assert sec.STATES != sec.COUNTIES


def test_recs_format():
    """
    Every record follows the format in the module docstring:
    feature -> action -> {user_list: [...], checks: {...}}.
    """
    for feature, actions in sec.read().items():
        assert isinstance(actions, dict)
        for action, rec in actions.items():
            assert action in ACTIONS
            assert isinstance(rec[sec.USER_LIST], list)
            assert isinstance(rec[sec.CHECKS], dict)
            for check, required in rec[sec.CHECKS].items():
                assert isinstance(check, str)
                assert isinstance(required, bool)


def test_read_feature():
    feature = sec.read_feature(sec.STATES)
    assert isinstance(feature, dict)
    assert sec.CREATE in feature


def test_read_feature_unknown():
    assert sec.read_feature('no_such_feature') is None


def test_needs_recs_loads_recs_when_missing():
    with patch.object(sec, 'security_recs', None):
        sec.read_feature(sec.STATES)
        assert sec.security_recs is not None


def test_needs_recs_does_not_reload():
    with patch.object(sec, 'security_recs', sec.temp_recs), \
            patch.object(sec, 'read', autospec=True) as mock_read:
        sec.read_feature(sec.STATES)
    mock_read.assert_not_called()


def test_needs_recs_keeps_name():
    assert sec.read_feature.__name__ == 'read_feature'
    assert sec.is_permitted.__name__ == 'is_permitted'


@pytest.mark.parametrize('action', ACTIONS)
def test_is_permitted_allows_everyone_for_now(action):
    """
    is_permitted() is a placeholder that allows every action.
    Change this test when real permission checks are added.
    """
    assert sec.is_permitted(sec.STATES, action, 'anyone@example.com')

def test_read_feature_counties_has_no_rec_yet():
    """
    Counties will have no security record yet, so they are open to all.
    """
    assert sec.read_feature(sec.COUNTIES) is None
