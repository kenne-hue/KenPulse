from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='notes')


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    is_admin = db.Column(db.Boolean, default=False)
    notes = db.relationship('Note', back_populates='user')
    reports = db.relationship('Report', back_populates='user')


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='Pending')
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    image_url = db.Column(db.String(200), nullable=True)
    resolution_proof = db.Column(db.String(200), nullable=True)
    resolution_description = db.Column(db.Text, nullable=True)
    proof_verified = db.Column(db.Boolean, default=False)
    first_response_time = db.Column(db.DateTime(timezone=True), nullable=True)
    resolution_time = db.Column(db.DateTime(timezone=True), nullable=True)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    user = db.relationship('User', back_populates='reports')

    def __init__(self, **kwargs):
        super(Report, self).__init__(**kwargs)
        self.first_response_time = None
        self.resolution_time = None
        self.last_updated = func.now()

    def update_status(self, new_status):
        """Update the report status and track timing metrics"""
        if self.status != new_status:
            if new_status == 'In Progress' and self.first_response_time is None:
                self.first_response_time = func.now()
            elif new_status == 'Resolved' and self.resolution_time is None:
                self.resolution_time = func.now()
            self.status = new_status
            self.last_updated = func.now()
            db.session.commit()


class IoTDevice(db.Model):
    __tablename__ = 'iot_device'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False)  # ESP32 MAC address or unique identifier
    name = db.Column(db.String(100))
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='Active')  # Active, Inactive, Maintenance
    last_seen = db.Column(db.DateTime(timezone=True), default=func.now())
    date_added = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='devices')
    data = db.relationship('DeviceData', back_populates='device')


class DeviceData(db.Model):
    __tablename__ = 'device_data'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('iot_device.id'))
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    air_quality = db.Column(db.Float)
    device = db.relationship('IoTDevice', back_populates='data')