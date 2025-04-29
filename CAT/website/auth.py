from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
from flask_mail import Message
from flask import current_app


auth = Blueprint('auth', __name__)


@auth.route('/auth-gateway')
def auth_gateway():
    return render_template("auth_gateway.html", user=current_user)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember_me') == 'on'
        
        if not email or not password:
            flash('Please fill in all fields.', category='error')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember=remember)
                flash('Logged in successfully!', category='success')
                return redirect(url_for('views.home'))
            else:
                flash('Invalid password.', category='error')
        else:
            flash('No account found with this email.', category='error')
    
    return render_template("login.html", user=current_user)


@auth.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Please fill in all fields.', category='error')
            return redirect(url_for('auth.admin_login'))

        user = User.query.filter_by(email=email).first()
        if user and user.is_admin:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.admin_dashboard'))
            else:
                flash('Invalid password.', category='error')
        else:
            flash('Invalid email or not an admin account.', category='error')

    return render_template("admin_login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.auth_gateway'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        if not all([email, first_name, last_name, password1, password2]):
            flash('Please fill in all fields.', category='error')
            return redirect(url_for('auth.sign_up'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4: # type: ignore
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2: # type: ignore
            flash('First name must be greater than 1 character.', category='error')
        elif len(last_name) < 2: # type: ignore
            flash('Last name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7: # type: ignore
            flash('Password must be at least 7 characters.', category='error')
        else:
            new_user = User(
                email=email, # type: ignore
                first_name=first_name, # type: ignore
                last_name=last_name, # type: ignore
                password=generate_password_hash(password1, method='pbkdf2:sha256') # type: ignore
            )
            db.session.add(new_user)
            db.session.commit()

            # Send welcome email
            msg = Message('Welcome to KenPulse!',
                        sender='your-email@gmail.com',  # Replace with your email
                        recipients=[email])
            msg.body = f'''
            Hello {first_name},

            Welcome to KenPulse! Your account has been successfully created.

            You can now:
            - Report issues in your community
            - Track the status of your reports
            - Receive updates when issues are resolved

            Best regards,
            The KenPulse Team
            '''
            mail.send(msg)

            login_user(new_user, remember=True)
            flash('Account created! A welcome email has been sent to your inbox.', category='success')
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)


@auth.route('/admin/sign-up', methods=['GET', 'POST'])
def admin_sign_up():
    if request.method == 'GET':
        return render_template('admin_sign_up.html', user=current_user)
    
    email = request.form.get('email')
    first_name = request.form.get('firstName')
    last_name = request.form.get('lastName')
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')
    adminCode = request.form.get('adminCode')

    if not all([email, first_name, last_name, password1, password2, adminCode]):
        flash('Please fill in all fields.', category='error')
        return redirect(url_for('auth.admin_sign_up'))

    user = User.query.filter_by(email=email).first()
    if user:
        flash('Email already exists.', category='error')
    elif len(email) < 4: # type: ignore
        flash('Email must be greater than 3 characters.', category='error')
    elif len(first_name) < 2: # type: ignore
        flash('First name must be greater than 1 character.', category='error')
    elif len(last_name) < 2: # type: ignore
        flash('Last name must be greater than 1 character.', category='error')
    elif password1 != password2:
        flash('Passwords don\'t match.', category='error')
    elif len(password1) < 7: # type: ignore
        flash('Password must be at least 7 characters.', category='error')
    elif adminCode != current_app.config['ADMIN_ACCESS_CODE']:
        flash('Invalid admin access code.', category='error')
    else:
        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=generate_password_hash(password1, method='pbkdf2:sha256'),
            is_admin=True
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user, remember=True)
        flash('Admin account created successfully!', category='success')
        return redirect(url_for('views.admin_dashboard'))

    return render_template("admin_sign_up.html", user=current_user)