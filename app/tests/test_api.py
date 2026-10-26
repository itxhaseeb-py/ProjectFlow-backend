
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.dependencies import get_db

# Import models so every table is registered in Base.metadata.
from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.task import Task  # noqa: F401


# ---------------------------------------------------------
# TEST DATABASE CONFIGURATION
# ---------------------------------------------------------

# Reuse the PostgreSQL server settings, but select the
# dedicated test database instead of the development DB.
TEST_DATABASE_URL = make_url(settings.DATABASE_URL).set(
    database="projectflow_test_db"
)

# Safety guard: never run these tests against projectflow_db.
if TEST_DATABASE_URL.database != "projectflow_test_db":
    raise RuntimeError("Tests must use projectflow_test_db.")

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------
# FIXTURES: SHARED TEST SETUP
# ---------------------------------------------------------

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Give each test a clean schema in the dedicated test DB."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestSessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Make API requests use the test database session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def register_user(
    client: TestClient,
    username: str = "alice_test",
    email: str = "alice@example.com",
    password: str = "StrongPassword123!",
) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_user(
    client: TestClient,
    email: str = "alice@example.com",
    password: str = "StrongPassword123!",
) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_project(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Test Project",
) -> dict:
    response = client.post(
        "/projects/",
        json={
            "name": name,
            "description": "Created by an automated test",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_task(
    client: TestClient,
    headers: dict[str, str],
    project_id: int,
    title: str = "Test Task",
) -> dict:
    response = client.post(
        f"/tasks/projects/{project_id}",
        json={
            "title": title,
            "description": "Created by an automated test",
            "status": "To Do",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------
# HEALTH AND AUTHENTICATION TESTS
# ---------------------------------------------------------

def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_register_user(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "username": "alice_test",
            "email": "alice@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "alice_test"
    assert data["email"] == "alice@example.com"
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_username_is_rejected(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/auth/register",
        json={
            "username": "alice_test",
            "email": "another@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 409


def test_duplicate_email_is_rejected(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/auth/register",
        json={
            "username": "another_user",
            "email": "ALICE@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 409


def test_login_returns_access_token(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "alice@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"].lower() == "bearer"


def test_login_rejects_wrong_password(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "alice@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_current_user_profile(client: TestClient) -> None:
    register_user(client)
    token = login_user(client)

    response = client.get(
        "/auth/me",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["username"] == "alice_test"
    assert response.json()["email"] == "alice@example.com"


def test_protected_route_rejects_missing_token(
    client: TestClient,
) -> None:
    response = client.get("/projects/")

    assert response.status_code == 401


def test_protected_route_rejects_invalid_token(
    client: TestClient,
) -> None:
    response = client.get(
        "/projects/",
        headers=auth_headers("not.a.valid.token"),
    )

    assert response.status_code == 401


def test_registration_rejects_invalid_input(
    client: TestClient,
) -> None:
    response = client.post(
        "/auth/register",
        json={
            "username": "ab",
            "email": "not-an-email",
            "password": "short",
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# PROJECT CRUD AND AUTHORIZATION TESTS
# ---------------------------------------------------------

def test_create_project(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))

    project = create_project(client, headers)

    assert project["name"] == "Test Project"
    assert project["owner_id"] > 0


def test_list_projects_and_pagination(
    client: TestClient,
) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))

    create_project(client, headers, "Project One")
    create_project(client, headers, "Project Two")

    response = client.get(
        "/projects/?limit=1&offset=0",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_single_project(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)

    response = client.get(
        f"/projects/{project['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == project["id"]


def test_update_project(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)

    response = client.patch(
        f"/projects/{project['id']}",
        json={"name": "Updated Project"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Project"


def test_delete_project(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)

    response = client.delete(
        f"/projects/{project['id']}",
        headers=headers,
    )

    assert response.status_code == 204

    missing = client.get(
        f"/projects/{project['id']}",
        headers=headers,
    )
    assert missing.status_code == 404


def test_user_cannot_access_another_users_project(
    client: TestClient,
) -> None:
    register_user(client)
    alice_headers = auth_headers(login_user(client))
    project = create_project(client, alice_headers)

    register_user(
        client,
        username="bob_test",
        email="bob@example.com",
    )
    bob_headers = auth_headers(
        login_user(client, email="bob@example.com")
    )

    response = client.get(
        f"/projects/{project['id']}",
        headers=bob_headers,
    )

    assert response.status_code == 404


def test_project_creation_rejects_blank_name(
    client: TestClient,
) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))

    response = client.post(
        "/projects/",
        json={"name": "   "},
        headers=headers,
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# TASK CRUD AND AUTHORIZATION TESTS
# ---------------------------------------------------------

def test_create_task(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)

    task = create_task(client, headers, project["id"])

    assert task["title"] == "Test Task"
    assert task["project_id"] == project["id"]
    assert task["status"] == "To Do"


def test_list_tasks_for_project(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)

    create_task(client, headers, project["id"], "Task One")
    create_task(client, headers, project["id"], "Task Two")

    response = client.get(
        f"/tasks/projects/{project['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_single_task(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)
    task = create_task(client, headers, project["id"])

    response = client.get(
        f"/tasks/{task['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == task["id"]


def test_update_task(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)
    task = create_task(client, headers, project["id"])

    response = client.patch(
        f"/tasks/{task['id']}",
        json={
            "title": "Updated Task",
            "status": "In Progress",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Task"
    assert response.json()["status"] == "In Progress"


def test_delete_task(client: TestClient) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)
    task = create_task(client, headers, project["id"])

    response = client.delete(
        f"/tasks/{task['id']}",
        headers=headers,
    )

    assert response.status_code == 204

    missing = client.get(
        f"/tasks/{task['id']}",
        headers=headers,
    )
    assert missing.status_code == 404


def test_cannot_create_task_in_another_users_project(
    client: TestClient,
) -> None:
    register_user(client)
    alice_headers = auth_headers(login_user(client))
    project = create_project(client, alice_headers)

    register_user(
        client,
        username="bob_test",
        email="bob@example.com",
    )
    bob_headers = auth_headers(
        login_user(client, email="bob@example.com")
    )

    response = client.post(
        f"/tasks/projects/{project['id']}",
        json={"title": "Unauthorized Task"},
        headers=bob_headers,
    )

    assert response.status_code == 404


def test_user_cannot_access_another_users_task(
    client: TestClient,
) -> None:
    register_user(client)
    alice_headers = auth_headers(login_user(client))
    project = create_project(client, alice_headers)
    task = create_task(client, alice_headers, project["id"])

    register_user(
        client,
        username="bob_test",
        email="bob@example.com",
    )
    bob_headers = auth_headers(
        login_user(client, email="bob@example.com")
    )

    response = client.get(
        f"/tasks/{task['id']}",
        headers=bob_headers,
    )

    assert response.status_code == 404


def test_task_rejects_invalid_status(
    client: TestClient,
) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)

    response = client.post(
        f"/tasks/projects/{project['id']}",
        json={
            "title": "Invalid Status Task",
            "status": "Finished Forever",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_task_rejects_blank_title(
    client: TestClient,
) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))
    project = create_project(client, headers)

    response = client.post(
        f"/tasks/projects/{project['id']}",
        json={"title": "   "},
        headers=headers,
    )

    assert response.status_code == 422


def test_task_creation_rejects_missing_project(
    client: TestClient,
) -> None:
    register_user(client)
    headers = auth_headers(login_user(client))

    response = client.post(
        "/tasks/projects/999999",
        json={"title": "Task without a project"},
        headers=headers,
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# DATABASE CLEANUP
# ---------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def dispose_test_engine() -> Generator[None, None, None]:
    """Release database connections after the test suite."""
    yield
    test_engine.dispose()
