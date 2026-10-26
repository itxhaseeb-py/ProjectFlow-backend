from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import Task


def create_task(
    db: Session,
    title: str,
    description: str | None,
    project_id: int,
    status: str = "To Do",
) -> Task:
    task = Task(
        title=title.strip(),
        description=description,
        project_id=project_id,
        status=status,
    )

    db.add(task)
    db.flush()

    return task


def get_task_by_id(
    db: Session,
    task_id: int,
) -> Task | None:
    statement = select(Task).where(Task.id == task_id)
    return db.scalar(statement)


def get_task_by_id_for_owner(
    db: Session,
    task_id: int,
    owner_id: int,
) -> Task | None:
    statement = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(
            Task.id == task_id,
            Project.owner_id == owner_id,
        )
    )

    return db.scalar(statement)


def get_tasks_for_project(
    db: Session,
    project_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[Task]:
    statement = (
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.id)
        .limit(limit)
        .offset(offset)
    )

    return list(db.scalars(statement).all())


def update_task(
    db: Session,
    task: Task,
    updates: dict,
) -> Task:
    allowed_fields = {"title", "description", "status"}

    for field, value in updates.items():
        if field not in allowed_fields:
            raise ValueError(f"Unsupported task field: {field}")

        if field == "title":
            value = value.strip()

        setattr(task, field, value)

    db.flush()

    return task


def delete_task(
    db: Session,
    task: Task,
) -> None:
    db.delete(task)
    db.flush()