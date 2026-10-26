
from sqlalchemy.orm import Session

from app.models.task import Task
from app.repositories.projects import get_project_by_id_for_owner
from app.repositories.tasks import (
    create_task as repository_create_task,
    delete_task as repository_delete_task,
    get_task_by_id_for_owner,
    get_tasks_for_project,
    update_task as repository_update_task,
)
from app.schemas.task import TaskCreate, TaskUpdate


def create_task(
    db: Session,
    project_id: int,
    owner_id: int,
    data: TaskCreate,
) -> Task:
    project = get_project_by_id_for_owner(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        raise LookupError("Project not found")

    try:
        task = repository_create_task(
            db=db,
            title=data.title,
            description=data.description,
            project_id=project.id,
            status=data.status,
        )

        db.commit()
        db.refresh(task)

        return task

    except Exception:
        db.rollback()
        raise


def list_tasks(
    db: Session,
    project_id: int,
    owner_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[Task]:
    project = get_project_by_id_for_owner(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        raise LookupError("Project not found")

    return get_tasks_for_project(
        db=db,
        project_id=project.id,
        limit=limit,
        offset=offset,
    )


def get_task(
    db: Session,
    task_id: int,
    owner_id: int,
) -> Task:
    task = get_task_by_id_for_owner(
        db=db,
        task_id=task_id,
        owner_id=owner_id,
    )

    if task is None:
        raise LookupError("Task not found")

    return task


def update_task(
    db: Session,
    task_id: int,
    owner_id: int,
    data: TaskUpdate,
) -> Task:
    task = get_task(db, task_id, owner_id)

    updates = data.model_dump(exclude_unset=True)

    if "title" in updates and updates["title"] is None:
        raise ValueError("Task title cannot be null")

    if "status" in updates and updates["status"] is None:
        raise ValueError("Task status cannot be null")

    if not updates:
        return task

    try:
        task = repository_update_task(
            db=db,
            task=task,
            updates=updates,
        )

        db.commit()
        db.refresh(task)

        return task

    except Exception:
        db.rollback()
        raise


def delete_task(
    db: Session,
    task_id: int,
    owner_id: int,
) -> None:
    task = get_task(db, task_id, owner_id)

    try:
        repository_delete_task(db=db, task=task)
        db.commit()

    except Exception:
        db.rollback()
        raise
