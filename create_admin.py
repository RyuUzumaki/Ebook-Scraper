from app import app, db, bcrypt
from models import User


def create_admin_user():
    with app.app_context():
        # 1. Create tables if they don't exist
        db.create_all()

        # 2. Check if admin already exists to prevent duplicates
        existing_admin = db.session.get(
            User, 1
        )  # Checks ID 1, or query by username below
        existing_user = User.query.filter_by(username="admin").first()

        if existing_user:
            print("❌ User 'admin' already exists.")
            # Optional: Upgrade existing user to admin if needed
            if not existing_user.is_admin:
                existing_user.is_admin = True
                db.session.commit()
                print("   -> Updated existing 'admin' user to have Admin privileges.")
            return

        # 3. Create the Admin User
        # You can change the password 'admin123' to whatever you want
        hashed_password = bcrypt.generate_password_hash("admin123").decode("utf-8")

        new_admin = User(
            username="admin",
            password_hash=hashed_password,
            is_admin=True,  # This is the key field!
        )

        db.session.add(new_admin)
        db.session.commit()

        print("✅ Admin user created successfully!")
        print("   Username: admin")
        print("   Password: admin123")


if __name__ == "__main__":
    create_admin_user()
