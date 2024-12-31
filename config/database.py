import os

class DB_Config:
    """Database configuration class."""
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///users.db')  # Default to 'users.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
