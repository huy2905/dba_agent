from fastapi.testclient import TestClient

from app.main import app
from app.planner import PlanError, plan
from app.service import chat
from app.skills import get_query

client = TestClient(app)


def test_health():
    assert client.get('/api/health').json()['ok'] is True


def test_targets_hide_credentials():
    targets = client.get('/api/targets').json()
    assert targets[0]['id'] == 'demo-pg'
    assert 'dsn_env' not in targets[0]


def test_demo_storage():
    out = chat('demo-pg', 'Kiểm tra dung lượng các database')
    assert out['is_demo'] is True
    assert out['skill_id'] == 'check_database_size'
    assert out['row_count'] >= 1


def test_demo_user_found():
    out = chat('demo-pg', 'Kiểm tra user app_user có tồn tại không?')
    assert out['skill_id'] == 'check_user_status'
    assert out['rows'][0]['role_name'] == 'app_user'


def test_demo_user_not_found():
    out = chat('demo-pg', 'Kiểm tra user missing_user')
    assert out['row_count'] == 0


def test_table_skill():
    assert plan('top 10 bảng lớn nhất')[0]['skill_id'] == 'check_table_size'


def test_no_arbitrary_sql_or_mutation():
    try:
        plan('DROP TABLE customers')
        raise AssertionError('Mutation request should be rejected')
    except PlanError:
        pass
    assert 'DROP' not in get_query('postgresql', 'check_database_size').sql.upper()


def test_unknown_target():
    response = client.post('/api/chat', json={'target_id': 'unknown', 'message': 'dung luong'})
    assert response.status_code == 400


def test_api_chat_demo():
    response = client.post('/api/chat', json={'target_id': 'demo-pg', 'message': 'Kiểm tra tablespace'})
    assert response.status_code == 200
    assert response.json()['skill_id'] == 'check_tablespace'
