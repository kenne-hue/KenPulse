from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from .models import Note, Report, User, IoTDevice, DeviceData
from . import db
import json
import os
from werkzeug.utils import secure_filename
from sqlalchemy.sql import func
import serial
import serial.tools.list_ports
import time
from website.utils.esp32_utils import ESP32Communicator
from .analytics import Analytics
import base64
from datetime import datetime

views = Blueprint('views', __name__)

# Configure upload folder
UPLOAD_FOLDER = 'website/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create a global ESP32 communicator instance
esp32_communicator = ESP32Communicator()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@views.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST': 
        note_text = request.form.get('note')
        if not note_text or len(note_text) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note()
            new_note.data = note_text
            new_note.user_id = current_user.id
            db.session.add(new_note)
            db.session.commit()
            flash('Note added!', category='success')

    # Get the 3 most recent reports with their timestamps
    recent_reports = Report.query.order_by(Report.timestamp.desc()).limit(3).all()
    
    # Get stats for the counter animation
    stats = {
        'reports_count': Report.query.count(),
        'resolved_count': Report.query.filter_by(status='Resolved').count(),
        'pending_count': Report.query.filter_by(status='Pending').count()
    }

    return render_template("home.html", user=current_user, recent_reports=recent_reports, stats=stats)


@views.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        image_url = None

        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(str(UPLOAD_FOLDER), exist_ok=True)
                file_path = os.path.join(str(UPLOAD_FOLDER), filename)
                file.save(file_path)
                image_url = f'/static/uploads/{filename}'

        if not title or len(title) < 1:
            flash('Title is too short!', category='error')
        else:
            new_report = Report()
            new_report.title = title
            new_report.description = description
            new_report.location = location
            new_report.image_url = image_url
            new_report.user_id = current_user.id
            db.session.add(new_report)
            db.session.commit()
            flash('Report submitted!', category='success')
            return redirect(url_for('views.track_resolutions'))

    return render_template("report.html", user=current_user)


@views.route('/delete-note', methods=['POST'])
@login_required
def delete_note():  
    note = json.loads(request.data)
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()
    return jsonify({})


@views.route('/track-resolutions')
@login_required
def track_resolutions():
    # Get all reports ordered by timestamp
    reports = Report.query.order_by(Report.timestamp.desc()).all()
    return render_template("track_resolutions.html", user=current_user, reports=reports)

@views.route('/about')
def about():
    return render_template("about.html", user=current_user)

@views.route('/terms')
def terms():
    return render_template("terms.html", user=current_user)

@views.route('/privacy')
def privacy():
    return render_template("privacy.html", user=current_user)

@views.route('/contact')
def contact():
    return render_template("contact.html", user=current_user)

@views.route('/faq')
def faq():
    return render_template("faq.html", user=current_user)

@views.route('/profile')
@login_required
def profile():
    # Get user's recent reports
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.timestamp.desc()).all()
    return render_template("profile.html", user=current_user, reports=reports)

@views.route('/delete-report', methods=['POST'])
@login_required
def delete_report():
    data = request.get_json()
    report_id = data.get('reportId')
    
    if not report_id:
        return jsonify({'error': 'Report ID is required'}), 400
        
    report = Report.query.get(report_id)
    
    if not report:
        return jsonify({'error': 'Report not found'}), 404
        
    if report.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        # Delete associated files if they exist
        if report.image_url:
            try:
                file_path = os.path.join(current_app.root_path, report.image_url.lstrip('/'))
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting image file: {e}")
                
        if report.resolution_proof:
            try:
                file_path = os.path.join(current_app.root_path, report.resolution_proof.lstrip('/'))
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting resolution proof file: {e}")
        
        # Delete the report from the database
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@views.route('/submit-proof', methods=['GET', 'POST'])
@login_required
def submit_proof():
    if request.method == 'POST':
        # Validate CSRF token
        if not request.form.get('csrf_token'):
            flash('Invalid request. Please try again.', category='error')
            return redirect(url_for('views.track_resolutions'))
            
        report_id = request.form.get('report_id')
        description = request.form.get('description')
        photo = request.files.get('photo')
        captured_photo = request.form.get('captured_photo')
        
        if not description:
            flash('Please provide a resolution description.', category='error')
            return redirect(url_for('views.submit_proof', report_id=report_id))
            
        report = Report.query.get(report_id)
        if not report:
            flash('Report not found.', category='error')
            return redirect(url_for('views.track_resolutions'))
            
        if report.status == 'Resolved':
            flash('This report has already been resolved.', category='error')
            return redirect(url_for('views.track_resolutions'))
            
        try:
            # Handle file upload if provided
            if photo and allowed_file(photo.filename) and photo.filename:
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
                report.resolution_proof = os.path.join('static/uploads', filename)
            # Handle camera capture if provided
            elif captured_photo:
                try:
                    # Decode base64 image
                    image_data = captured_photo.split(',')[1]
                    image_binary = base64.b64decode(image_data)
                    
                    # Generate unique filename
                    filename = f'proof_{report_id}_{int(time.time())}.jpg'
                    photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    
                    # Save the image
                    with open(photo_path, 'wb') as f:
                        f.write(image_binary)
                    
                    report.resolution_proof = os.path.join('static/uploads', filename)
                except Exception as e:
                    flash('Error processing captured photo. Please try again.', category='error')
                    return redirect(url_for('views.submit_proof', report_id=report_id))
            
            # Update report
            report.resolution_description = description
            report.status = 'Pending Verification'
            report.resolution_time = datetime.utcnow()
            db.session.commit()
            
            flash('Proof submitted successfully!', category='success')
            return redirect(url_for('views.track_resolutions'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while submitting the proof. Please try again.', category='error')
            return redirect(url_for('views.submit_proof', report_id=report_id))
    
    # GET request - show the form
    report_id = request.args.get('report_id')
    if not report_id:
        flash('No report specified.', category='error')
        return redirect(url_for('views.track_resolutions'))
        
    report = Report.query.get(report_id)
    if not report:
        flash('Report not found.', category='error')
        return redirect(url_for('views.track_resolutions'))
        
    if report.status == 'Resolved':
        flash('This report has already been resolved.', category='error')
        return redirect(url_for('views.track_resolutions'))
        
    return render_template('submit_proof.html', report=report, user=current_user)

@views.route('/get-report/<int:report_id>')
@login_required
def get_report(report_id):
    report = Report.query.get_or_404(report_id)
    return jsonify({
        'title': report.title,
        'status': report.status,
        'timestamp': report.timestamp.strftime('%B %d, %Y at %I:%M %p'),
        'description': report.description,
        'location': report.location,
        'reporterName': report.user.first_name,
        'reporterRole': 'Local Resident',
        'imageUrl': report.image_url if report.image_url else None
    })

@views.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')

        if not all([first_name, last_name, email]):
            flash('All fields are required.', category='error')
        else:
            if len(first_name) < 2: # type: ignore
                flash('First name must be greater than 1 character.', category='error')
            elif last_name and len(last_name) < 2:
                flash('Last name must be greater than 1 character.', category='error')
            elif email and len(email) < 4:
                flash('Email must be greater than 3 characters.', category='error')
            else:
                # Check if email is already taken by another user
                existing_user = User.query.filter_by(email=email).first()
                if existing_user and existing_user.id != current_user.id:
                    flash('Email already exists.', category='error')
                else:
                    current_user.first_name = first_name
                    current_user.last_name = last_name
                    current_user.email = email
                    db.session.commit()
                    flash('Profile updated!', category='success')
                    return redirect(url_for('views.profile'))

    return render_template("edit_profile.html", user=current_user)

@views.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Unauthorized access.', category='error')
        return redirect(url_for('views.home'))
        
    # Get statistics
    stats = {
        'total_users': User.query.count(),
        'active_reports': Report.query.filter(Report.status != 'Resolved').count(), # type: ignore
        'resolved_reports': Report.query.filter_by(status='Resolved').count()
    }
    
    # Get reports pending verification
    pending_verification = Report.query.filter_by(status='Pending Verification').all()
    
    # Get recent activity
    recent_activity = Report.query.order_by(Report.timestamp.desc()).limit(10).all()
    
    # Get all users for the user management section
    users = User.query.all()
    
    return render_template('admin/dashboard.html', 
                         user=current_user,
                         stats=stats,
                         users=users,
                         pending_verification=pending_verification,
                         recent_activity=recent_activity)

@views.route('/admin/user-reports/<int:user_id>')
@login_required
def admin_user_reports(user_id):
    if not current_user.is_admin:
        return render_template('unauthorized.html')
    user = User.query.get_or_404(user_id)
    reports = Report.query.filter_by(user_id=user_id).order_by(Report.timestamp.desc()).all()
    return render_template('admin/user_reports.html', user=current_user, target_user=user, reports=reports)

@views.route('/admin/suspend-user/<int:user_id>', methods=['POST'])
@login_required
def suspend_user(user_id):
    if not current_user.is_admin:
        return render_template('unauthorized.html')
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return jsonify({'success': True})

@views.route('/admin/activate-user/<int:user_id>', methods=['POST'])
@login_required
def activate_user(user_id):
    if not current_user.is_admin:
        return render_template('unauthorized.html')
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    return jsonify({'success': True})

@views.route('/iot/devices')
@login_required
def iot_devices():
    devices = IoTDevice.query.filter_by(user_id=current_user.id).all()
    return render_template('iot/devices.html', user=current_user, devices=devices)

@views.route('/iot/device/<int:device_id>')
@login_required
def device_details(device_id):
    device = IoTDevice.query.get_or_404(device_id)
    if device.user_id != current_user.id:
        flash('Access denied.', category='error')
        return redirect(url_for('views.iot_devices'))
    
    # Get recent data points
    recent_data = DeviceData.query.filter_by(device_id=device_id)\
        .order_by(DeviceData.timestamp.desc())\
        .limit(100)\
        .all()
    
    return render_template('iot/device_details.html', 
                         user=current_user,
                         device=device,
                         recent_data=recent_data)

@views.route('/api/iot/register', methods=['POST'])
def register_device():
    data = request.get_json()
    if not data or 'device_id' not in data:
        return jsonify({'success': False, 'message': 'Invalid request data'}), 400

    new_device = IoTDevice(
        device_id=data['device_id'],  # type: ignore
        name=data.get('name', 'New Device'), # type: ignore
        location=data.get('location', 'Unknown'), # type: ignore
        user_id=current_user.id  # Use the current user's ID instead of device_id # type: ignore
    )
    db.session.add(new_device)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Device registered successfully'})

@views.route('/api/iot/data', methods=['POST'])
def receive_device_data():
    data = request.get_json()
    if not data or 'device_id' not in data:
        return jsonify({'success': False, 'message': 'Invalid request data'}), 400

    device = IoTDevice.query.filter_by(device_id=data['device_id']).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    new_data = DeviceData(
        device_id=device.id, # type: ignore
        temperature=data.get('temperature', None), # type: ignore
        humidity=data.get('humidity', None),  # type: ignore
        air_quality=data.get('air_quality', None) # type: ignore
    )
    device.last_seen = func.now()
    db.session.add(new_data)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Data received successfully'})

@views.route('/admin/reports')
@login_required
def admin_reports():
    if not current_user.is_admin:
        return render_template('unauthorized.html')
    reports = Report.query.order_by(Report.timestamp.desc()).all()
    return render_template('admin/reports.html', user=current_user, reports=reports)

@views.route('/admin/settings')
@login_required
def admin_settings():
    if not current_user.is_admin:
        return render_template('unauthorized.html')
    return render_template('admin/settings.html', user=current_user)

@views.route('/admin/activity-logs')
@login_required
def admin_activity_logs():
    if not current_user.is_admin:
        return render_template('unauthorized.html')
    logs = Report.query.order_by(Report.timestamp.desc()).all()
    return render_template('admin/activity_logs.html', user=current_user, logs=logs)

@views.route('/admin/update-report-status/<int:report_id>', methods=['POST'])
@login_required
def update_report_status(report_id):
    if not current_user.is_admin:
        return render_template('unauthorized.html')
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get('status')
    if new_status in ['Pending', 'In Progress', 'Resolved']:
        report.status = new_status
        db.session.commit()
        flash('Report status updated successfully!', category='success')
    return redirect(url_for('views.admin_reports'))

@views.route('/admin/update-settings', methods=['POST'])
@login_required
def update_settings():
    if not current_user.is_admin:
        return render_template('unauthorized.html')
    # Handle settings update logic here
    flash('Settings updated successfully!', category='success')
    return redirect(url_for('views.admin_settings'))

@views.route('/reports')
def all_reports():
    reports = Report.query.order_by(Report.timestamp.desc()).all()
    return render_template('reports.html', reports=reports)

@views.route('/admin/verify-report/<int:report_id>', methods=['POST'])
@login_required
def verify_report(report_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    report = Report.query.get_or_404(report_id)
    report.proof_verified = True
    report.status = 'Resolved'
    db.session.commit()
    
    flash('Report proof verified successfully!', category='success')
    return jsonify({'success': True})

@views.route('/admin/get-report/<int:report_id>', methods=['GET'])
@login_required
def get_report_details(report_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    report = Report.query.get_or_404(report_id)
    return jsonify({
        'title': report.title,
        'resolution_description': report.resolution_description,
        'resolution_proof': report.resolution_proof,
        'user': {
            'first_name': report.user.first_name,
            'last_name': report.user.last_name
        }
    })

@views.route('/submit-report', methods=['GET', 'POST'])
@login_required
def submit_report():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        image = request.files.get('image')
        video = request.files.get('video')
        audio = request.files.get('audio')
        document = request.files.get('document')
        
        if not title or not description or not location:
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('views.submit_report'))
            
        # Create new report
        new_report = Report(
            title=title,
            description=description,
            location=location,
            user_id=current_user.id,  # type: ignore
            status='pending'
        )
        db.session.add(new_report)
        db.session.commit()
        flash('Report submitted successfully!', category='success')
        return redirect(url_for('views.track_resolutions'))

    return render_template("submit_report.html", user=current_user)

@views.route('/esp32')
@login_required
def esp32():
    # Check if ESP32 is available
    esp32_available = esp32_communicator.is_esp32_available()
    ports = esp32_communicator.get_available_ports() if esp32_available else []
    
    return render_template('esp32.html', 
                         user=current_user, 
                         ports=ports,
                         esp32_available=esp32_available)

@views.route('/esp32/connect', methods=['POST'])
@login_required
def connect_esp32():
    if not esp32_communicator.is_esp32_available():
        return jsonify({'success': False, 'message': 'ESP32 is not available on this system'})
    
    port = request.form.get('port')
    if not port:
        return jsonify({'success': False, 'message': 'Port not specified'})
    
    success, message = esp32_communicator.connect(port)
    return jsonify({'success': success, 'message': message})

@views.route('/esp32/disconnect', methods=['POST'])
@login_required
def disconnect_esp32():
    success, message = esp32_communicator.disconnect()
    return jsonify({'success': success, 'message': message})

@views.route('/esp32/send-command', methods=['POST'])
@login_required
def send_command():
    if not esp32_communicator.is_connected():
        return jsonify({'success': False, 'message': 'Not connected to ESP32'})
    
    command = request.form.get('command')
    if not command:
        return jsonify({'success': False, 'message': 'No command specified'})
    
    success, response = esp32_communicator.send_command(command)
    return jsonify({'success': success, 'response': response})

@views.route('/esp32/status', methods=['GET'])
@login_required
def get_esp32_status():
    status = esp32_communicator.get_status()
    return jsonify({'status': status})

@views.route('/admin/delete-report/<int:report_id>', methods=['POST'])
@login_required
def admin_delete_report(report_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
    
    report = Report.query.get_or_404(report_id)
    
    try:
        # Delete associated files if they exist
        if report.image_url:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], report.image_url))
            except:
                pass  # Ignore if file doesn't exist
        
        if report.resolution_proof:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], report.resolution_proof))
            except:
                pass  # Ignore if file doesn't exist
        
        db.session.delete(report)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Report deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@views.route('/api/communication', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def http_communication():
    """
    Handle HTTP communication with proper method handling and response types.
    """
    try:
        if request.method == 'GET':
            # Handle GET request
            return jsonify({'status': 'success', 'message': 'GET request received'})
            
        elif request.method == 'POST':
            # Handle POST request
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            return jsonify({'status': 'success', 'message': 'Data received', 'data': data}), 201
            
        elif request.method == 'PUT':
            # Handle PUT request
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            return jsonify({'status': 'success', 'message': 'Data updated', 'data': data})
            
        elif request.method == 'DELETE':
            # Handle DELETE request
            data = request.get_json()
            if not data or 'id' not in data:
                return jsonify({'status': 'error', 'message': 'No ID provided'}), 400
            return jsonify({'status': 'success', 'message': 'Data deleted'})
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500