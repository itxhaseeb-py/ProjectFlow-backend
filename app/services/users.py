
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.users import get_user_by_id


def get_user_profile(db: Session, user_id: int) -> User:
    """
    Retrieve a user's profile by their database ID.

    Args:
        db: The active SQLAlchemy database session.
        user_id: The ID of the user whose profile is requested.

    Returns:
        The matching User model instance.

    Raises:
        LookupError: If the user does not exist.
    """
    user = get_user_by_id(db=db, user_id=user_id)

    if user is None:
        raise LookupError("User not found")

    return user
