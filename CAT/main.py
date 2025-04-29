import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from website import create_app
from flask_mail import Mail, Message
from website.models import Report, User
from flask_login import current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func

app = create_app()  # Use the create_app function from website package

# Flask-Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kenpulse254@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'kenpulse254@gmail.com'

mail = Mail(app)

# Define translations
translations = {
    'en': {
        'reports': 'Reports',
        'resolved': 'Resolved',
        'pending': 'Pending'
    },
    'sw': {
        'reports': 'Ripoti',
        'resolved': 'Imetatuliwa',
        'pending': 'Inasubiri'
    }
}

app.config['ADMIN_ACCESS_CODE'] = os.environ.get('ADMIN_ACCESS_CODE', 'admin123')

@app.route('/')
def index():
    return redirect(url_for('auth.auth_gateway'))
    
@app.route('/home')
def home():
    # Get the 3 most recent reports to display on homepage
    recent_reports = Report.query.order_by(Report.timestamp.desc()).limit(3).all()
    
    # Get stats for the counter animation
    stats = {
        'total': Report.query.count() or 0,
        'resolved': Report.query.filter_by(status='Resolved').count() or 0,
        'pending': Report.query.filter_by(status='Pending').count() or 0,
        'in_progress': Report.query.filter_by(status='In Progress').count() or 0,
    }
    
    # Calculate resolution rate
    stats['resolution_rate'] = int((stats['resolved'] / stats['total'] * 100) if stats['total'] > 0 else 0)
    
    # Determine which language to use (default to English)
    lang = session.get('lang', 'en')
    
    return render_template(
        'home.html',
        recent_reports=recent_reports,
        stats=stats,
        translations=translations[lang],
        current_user=current_user,
        lang=lang
    )

@app.route('/switch_language/<language>')
def switch_language(language):
    if language in ['en', 'sw']:
        session['lang'] = language
    return redirect(request.referrer or url_for('views.home'))

@app.route('/admin')
def admin():
    # Get recent activity
    recent_activity = Report.query.order_by(Report.timestamp.desc()).limit(10).all()
    
    return render_template(
        'admin.html',
        recent_activity=recent_activity
    )

@app.route('/track-resolutions')
@login_required
def track_resolutions():
    # Get all reports ordered by timestamp
    reports = Report.query.order_by(Report.timestamp.desc()).all()
    return render_template("track_resolutions.html", user=current_user, reports=reports)

@app.route('/submit-proof/<int:report_id>', methods=['GET', 'POST'])
@login_required
def submit_proof(report_id):
    report = Report.query.get_or_404(report_id)
    if request.method == 'POST':
        # Handle form submission
        pass
    return render_template('submit_proof.html', report=report)

if __name__ == '__main__':
    app.run(debug=True)