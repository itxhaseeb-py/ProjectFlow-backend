from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project


def create_project(
    db: Session,
    name: str,
    description: str | None,
    owner_id: int,
) -> Project:
    project = Project(
        name=name.strip(),
        description=description,
        owner_id=owner_id,
    )

    db.add(project)
    db.flush()

    return project


def get_project_by_id(
    db: Session,
    project_id: int,
) -> Project | None:
    statement = select(Project).where(Project.id == project_id)
    return db.scalar(statement)


def get_project_by_id_for_owner(
    db: Session,
    project_id: int,
    owner_id: int,
) -> Project | None:
    statement = select(Project).where(
        Project.id == project_id,
        Project.owner_id == owner_id,
    )

    return db.scalar(statement)


def get_projects_for_owner(
    db: Session,
    owner_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[Project]:
    statement = (
        select(Project)
        .where(Project.owner_id == owner_id)
        .order_by(Project.id)
        .limit(limit)
        .offset(offset)
    )

    return list(db.scalars(statement).all())


def update_project(
    db: Session,
    project: Project,
    updates: dict,
) -> Project:
    allowed_fields = {"name", "description"}

    for field, value in updates.items():
        if field not in allowed_fields:
            raise ValueError(f"Unsupported project field: {field}")

        if field == "name":
            value = value.strip()

        setattr(project, field, value)

    db.flush()

    return project


def delete_project(
    db: Session,
    project: Project,
) -> None:
    db.delete(project)
    db.flush()