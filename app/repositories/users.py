
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_id(db: Session, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id)
    return db.scalar(statement)


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(
        func.lower(User.email) == email.strip().lower()
    )
    return db.scalar(statement)


def get_user_by_username(
    db: Session,
    username: str,
) -> User | None:
    statement = select(User).where(
        func.lower(User.username) == username.strip().lower()
    )
    return db.scalar(statement)


def create_user(
    db: Session,
    username: str,
    email: str,
    password_hash: str,
) -> User:
    user = User(
        username=username.strip(),
        email=email.strip().lower(),
        password_hash=password_hash,
    )

    db.add(user)
    db.flush()

    return user
