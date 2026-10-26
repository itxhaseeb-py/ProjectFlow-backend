
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.users import (
    create_user,
    get_user_by_email,
    get_user_by_username,
)
from app.schemas.auth import RegisterRequest


def register_user(db: Session, data: RegisterRequest) -> User:
    existing_email = get_user_by_email(db, str(data.email))

    if existing_email is not None:
        raise ValueError("Email already registered")

    existing_username = get_user_by_username(db, data.username)

    if existing_username is not None:
        raise ValueError("Username already registered")

    password_hash = hash_password(data.password)

    try:
        user = create_user(
            db=db,
            username=data.username,
            email=str(data.email),
            password_hash=password_hash,
        )

        db.commit()
        db.refresh(user)

        return user

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Username or email already registered"
        ) from exc

    except Exception:
        db.rollback()
        raise


def login_user(
    db: Session,
    email: str,
    password: str,
) -> dict[str, str]:
    user = get_user_by_email(db, email)

    if user is None or not verify_password(
        password,
        user.password_hash,
    ):
        raise ValueError("Invalid email or password")

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
