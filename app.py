import requests
from flask import Flask, render_template, url_for, request, redirect, flash, abort
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from extensions import (
    db,
    bcrypt,
    login_manager,
    cache,
)
from flask_bcrypt import Bcrypt
from functools import wraps

from config import Config
from models import db, User, Favorite
from services.ebookFetcher import get_ebooks
from services.ebookDownloader import get_epub_link
from services.ebookDetails import get_single_book_details

app = Flask(__name__)
app.config.from_object(Config)

# -- CONFIGURE CACHE --
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300

# Initialize Extensions
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
cache.init_app(app)

login_manager.login_view = "login"  # type: ignore

# Create tables in MySQL if they don't exits
with app.app_context():
    db.create_all()


# --- ADMIN PROTECTION DECORATOR ---
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # If the user is not an admin, show a 403 Forbidden error
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


# --- ADMIN ROUTES ---
@app.route("/admin")
@admin_required
def admin_dashboard():
    # Fetch all users to display in the table
    users = User.query.all()
    return render_template("admin_dashboard.html", users=users)


@app.route("/admin/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for("admin_dashboard"))

    user_to_delete = db.session.get(User, user_id)

    if user_to_delete:
        # Optional: You might want to delete their favorites first if cascade isn't set
        # But our model has cascade="all, delete-orphan", so it handles it automatically.
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"User '{user_to_delete.username}' has been deleted.", "success")
    else:
        flash("User not found.", "warning")

    return redirect(url_for("admin_dashboard"))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- AUTH ROUTES ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("register"))

        # Hash password and save
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(username=username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


# --- FAVORITES ROUTE ---
@app.route("/add_favorites")
@login_required
def add_favorite():
    title = request.args.get("title")
    url = request.args.get("url")

    # Check if already favorited
    existing = Favorite.query.filter_by(user_id=current_user.id, book_url=url).first()

    if not existing:
        fav = Favorite(user_id=current_user.id, book_url=url, book_title=title)
        db.session.add(fav)
        db.session.commit()
        flash(f'Added "{title}" to favorites!', "success")
    else:
        flash("Already in favorites.", "info")

    return redirect(request.referrer)  # Go back to the previous page


@app.route("/remove_favorite")
@login_required
def remove_favorite():
    url = request.args.get("url")

    # Find the favorite entry
    fav = Favorite.query.filter_by(user_id=current_user.id, book_url=url).first()

    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash("Removed from favorites.", "info")
    else:
        flash("Item not found in favorites.", "warning")

    # Refresh the page the user was just on
    return redirect(request.referrer)


@app.route("/my_favorites")
@login_required
def my_favorites():
    # Get all favorites for current user
    user_favs = Favorite.query.filter_by(user_id=current_user.id).all()

    fav_urls = [f.book_url for f in user_favs]

    # Convert DB objects to a dictionary format that our HTML template expects
    # (Matching the format from ebookFetcher)
    formatted_books = []
    for fav in user_favs:
        formatted_books.append(
            {
                "title": fav.book_title,
                "link": fav.book_url,
                "summary": "Saved Favorite",  # Placeholder
            }
        )

    return render_template(
        "index.html",
        books=formatted_books,
        current_page=1,
        has_next=False,
        is_favorites=True,
        fav_urls=fav_urls,
    )


# Route: Home (Uses ebookFetcher)
@app.route("/")
def landing_page():
    return render_template("landing_page.html")


@app.route("/home")
def home():
    page = request.args.get("page", 1, type=int)
    search_term = request.args.get("query", default=None, type=str)
    category_filter = request.args.get("category", default=None, type=str)

    book_list, has_next = get_ebooks(
        page_number=page, search_query=search_term, category=category_filter
    )

    fav_urls = []
    if current_user.is_authenticated:
        fav_urls = [f.book_url for f in current_user.favorites]

    return render_template(
        "index.html",
        books=book_list,
        current_page=page,
        search_query=search_term,
        has_next=has_next,
        fav_urls=fav_urls,
        current_category=category_filter,
    )


# Route: Details (Uses ebookDetails)
@app.route("/details")
def show_details():
    url = request.args.get("url")

    page = request.args.get("page", 1, type=int)
    query = request.args.get("query", default=None, type=str)

    book_data = get_single_book_details(url)

    if book_data:
        return render_template("details.html", book=book_data, page=page, query=query)
    else:
        return "Error loading book details."


# Route: Download Proxy (Uses ebookDownloader)
@app.route("/download_book")
def download_book():
    book_url = request.args.get("url")

    # Get the direct .epub link using your scraper
    epub_link = get_epub_link(book_url)

    if not epub_link:
        return "Error: Could not find download link."

    # Redirect the browser to the file
    # BECAUSE it is a file download, the browser will NOT navigate away.
    # It will stay on your site and start the download in the background.
    return redirect(epub_link)


@app.route("/category/<category_name>")
def category(category_name):
    page = request.args.get("page", 1, type=int)

    # 1. NEW: Capture the search query if it exists
    query = request.args.get("query", default=None, type=str)

    # 2. Pass search_query to the fetcher
    book_list, has_next = get_ebooks(
        page_number=page,
        category=category_name,
        search_query=query,  # <--- Pass it here!
    )

    fav_urls = []
    if current_user.is_authenticated:
        fav_urls = [f.book_url for f in current_user.favorites]

    return render_template(
        "index.html",
        books=book_list,
        current_page=page,
        has_next=has_next,
        fav_urls=fav_urls,
        current_category=category_name,
        search_query=query,  # 3. Pass it back to template so the search bar keeps the text
    )


if __name__ == "__main__":
    app.run(debug=True)
