from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

db = SQLAlchemy()
DB_NAME = "database.db"
mail = Mail()
socketio = SocketIO()
migrate = Migrate()
csrf = CSRFProtect()

def format_timedelta(value):
    """Format a timedelta object into a human-readable string"""
    if not value:
        return "N/A"
    if isinstance(value, (int, float)):
        value = timedelta(seconds=value)
    days = value.days
    hours = value.seconds // 3600
    minutes = (value.seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hjshjhdjah kjshkjdhjs')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///website.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize CSRF protection first
    csrf.init_app(app)
    
    # Email configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'kenpulse254@gmail.com'
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = 'kenpulse254@gmail.com'
    
    # Admin configuration
    app.config['ADMIN_ACCESS_CODE'] = os.environ.get('ADMIN_ACCESS_CODE', 'admin123')
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    socketio.init_app(app)
    migrate.init_app(app, db)

    # Import models
    from .models import User, Note, Report

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    # Create database tables
    with app.app_context():
        db.create_all()

    # Add template filters
    app.jinja_env.filters['format_timedelta'] = format_timedelta

    # Register blueprints
    register_blueprints(app)

    return app

def register_blueprints(app):
    from .views import views
    from .auth import auth
    from .analytics import analytics
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(analytics, url_prefix='/')

def create_database(app):
    if not path.exists('website/' + DB_NAME):
        with app.app_context():
            db.create_all()
        print('Created Database!')