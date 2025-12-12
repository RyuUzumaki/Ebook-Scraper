from flask_login import UserMixin
from extensions import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # NEW: Admin Flag (Defaults to False for regular users)
    is_admin = db.Column(db.Boolean, default=False)

    favorites = db.relationship(
        "Favorite", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def __init__(self, username, password_hash, is_admin=False):
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_url = db.Column(db.String(500), nullable=False)
    book_title = db.Column(db.String(500), nullable=False)

    def __init__(self, user_id, book_url, book_title):
        self.user_id = user_id
        self.book_url = book_url
        self.book_title = book_title
