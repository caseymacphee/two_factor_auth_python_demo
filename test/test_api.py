import pytest
import json
import urllib
import arrow
from ..api import generate_code, is_code_valid, app, db, AuthCode
from ..settings import TEST_DB, RETRIES_ALLOWED


def teardown_module(module):
    if TEST_DB in app.config['SQLALCHEMY_DATABASE_URI']:
        db.drop_all()
    else:
        raise AttributeError(("The production database is turned on. "
                              "Flip settings.DEBUG to True"))


def setup_module(module):
    db.create_all()


@pytest.mark.parametrize("length, err", [
    (-1, AssertionError),
    (0, AssertionError),
    (1, None),
    (2, None),
    (3, None),
    (4, None),
    (5, None),
    (10, None),
])
def test_generate_code(length, err):
    if err:
        with pytest.raises(err):
            generate_code(length)
    else:
        code = generate_code(length)
        assert type(code) == int
        assert len(str(code)) == length


@pytest.mark.parametrize("ts, exp_window, expected", [
    (str(arrow.utcnow()), 10, True),
    (str(arrow.utcnow()), 0, False),
    (str(arrow.utcnow().replace(seconds=-60)), 60, False),
])
def test_is_code_valid(ts, exp_window, expected):
    res = is_code_valid(ts, exp_window=exp_window)
    assert res is expected

#
#def test_post_auth(app=app):
#    client = app.test_client()
#    auth_uuid = str(uuid.uuid1())
#    json_body = {"auth_id": auth_uuid}
#    length = len(json.dumps(json_body))
#    res = client.post('/', data=json_body,
#                      content_type='application/json',
#                      content_length=length)
#    assert res.status_code == 200


def test_get_auth_success(app=app):
    client = app.test_client()
    new_auth = AuthCode('jjj', 1234)
    new_auth.attempts = RETRIES_ALLOWED - 1
    db.session.add(new_auth)
    db.session.commit()
    query = urllib.urlencode(
        {'auth_id': new_auth.auth_id,
         'code': 1234,
         })
    with client:
        res = client.get('/?' + query)
    assert res.status_code == 200
    assert json.loads(res.data)['Authenticated'] is True


@pytest.mark.parametrize("auth_id, retries, retry", [
    ('aaa', RETRIES_ALLOWED - 1, False),
    ('bbb', 1, True),
])
def test_get_auth_attempts_fail(auth_id, retries, retry, app=app):
    client = app.test_client()
    new_auth = AuthCode(auth_id, 1234)
    new_auth.attempts = retries
    db.session.add(new_auth)
    db.session.commit()
    query = urllib.urlencode(
        {'auth_id': auth_id,
         'code': 1111,
         })
    with client:
        res = client.get('/?' + query)
    assert res.status_code == 200
    assert json.loads(res.data)['Authenticated'] is False
    assert json.loads(res.data)['Retry'] is retry
