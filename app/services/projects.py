
from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.projects import (
    create_project as repository_create_project,
    delete_project as repository_delete_project,
    get_project_by_id_for_owner,
    get_projects_for_owner,
    update_project as repository_update_project,
)
from app.schemas.project import ProjectCreate, ProjectUpdate


def create_project(
    db: Session,
    owner_id: int,
    data: ProjectCreate,
) -> Project:
    try:
        project = repository_create_project(
            db=db,
            name=data.name,
            description=data.description,
            owner_id=owner_id,
        )

        db.commit()
        db.refresh(project)
        return project

    except Exception:
        db.rollback()
        raise


def list_projects(
    db: Session,
    owner_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[Project]:
    return get_projects_for_owner(
        db=db,
        owner_id=owner_id,
        limit=limit,
        offset=offset,
    )


def get_project(
    db: Session,
    project_id: int,
    owner_id: int,
) -> Project:
    project = get_project_by_id_for_owner(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )

    if project is None:
        raise LookupError("Project not found")

    return project


def update_project(
    db: Session,
    project_id: int,
    owner_id: int,
    data: ProjectUpdate,
) -> Project:
    project = get_project(db, project_id, owner_id)
    updates = data.model_dump(exclude_unset=True)

    if "name" in updates and updates["name"] is None:
        raise ValueError("Project name cannot be null")

    if not updates:
        return project

    try:
        project = repository_update_project(
            db=db,
            project=project,
            updates=updates,
        )

        db.commit()
        db.refresh(project)
        return project

    except Exception:
        db.rollback()
        raise


def delete_project(
    db: Session,
    project_id: int,
    owner_id: int,
) -> None:
    project = get_project(db, project_id, owner_id)

    try:
        repository_delete_project(db=db, project=project)
        db.commit()

    except Exception:
        db.rollback()
        raise
