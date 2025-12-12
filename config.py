import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 1. SECRET KEY is required for sessions (Login)
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key-please-change"

    # 2. Database Connection URI
    # Format: mysql+mysqlconnector://USERNAME:PASSWORD@HOST/DB_NAME
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "site.db")

    # Turn off a feature we don't need to save memory
    SQLALCHEMY_TRACK_MODIFICATIONS = False
