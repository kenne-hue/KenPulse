from datetime import datetime, timedelta
from sqlalchemy import func, case, and_, text, cast, Float
from .models import Report, User
from . import db
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

analytics = Blueprint('analytics', __name__)

class Analytics:
    @staticmethod
    def get_report_stats():
        """Get overall report statistics"""
        total_reports = Report.query.count()
        resolved_reports = Report.query.filter_by(status='Resolved').count()
        pending_reports = Report.query.filter_by(status='Pending').count()
        in_progress_reports = Report.query.filter_by(status='In Progress').count()
        
        return {
            'total': total_reports,
            'resolved': resolved_reports,
            'pending': pending_reports,
            'in_progress': in_progress_reports,
            'resolution_rate': (resolved_reports / total_reports * 100) if total_reports > 0 else 0
        }

    @staticmethod
    def get_trends(days=30):
        """Get report trends over time"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get daily report counts
        daily_counts = db.session.query(
            func.date(Report.timestamp).label('date'),
            func.count(Report.id).label('count')
        ).filter(
            Report.timestamp >= start_date
        ).group_by(
            func.date(Report.timestamp)
        ).all()
        
        # Get status distribution
        status_distribution = db.session.query(
            Report.status,
            func.count(Report.id).label('count')
        ).filter(
            Report.timestamp >= start_date
        ).group_by(
            Report.status
        ).all()
        
        return {
            'daily_counts': [{'date': str(d[0]), 'count': d[1]} for d in daily_counts],
            'status_distribution': [{'status': d[0], 'count': d[1]} for d in status_distribution]
        }

    @staticmethod
    def get_user_activity():
        """Get user activity statistics"""
        total_users = User.query.count()
        
        # Get active users (users who have submitted reports in the last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        active_users = db.session.query(func.count(func.distinct(Report.user_id))).filter(
            Report.timestamp >= thirty_days_ago
        ).scalar()
        
        # Get top reporters
        top_reporters = db.session.query(
            User.first_name,
            User.last_name,
            func.count(Report.id).label('report_count')
        ).join(
            Report, User.id == Report.user_id
        ).group_by(
            User.id
        ).order_by(
            func.count(Report.id).desc()
        ).limit(5).all()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'top_reporters': [{'name': f"{r[0]} {r[1]}", 'count': r[2]} for r in top_reporters]
        }

    @staticmethod
    def get_location_insights():
        """Get insights based on report locations"""
        # Get top locations
        top_locations = db.session.query(
            Report.location,
            func.count(Report.id).label('count')
        ).group_by(
            Report.location
        ).order_by(
            func.count(Report.id).desc()
        ).limit(5).all()
        
        # Get location-based resolution rates
        location_resolution = db.session.query(
            Report.location,
            func.count(Report.id).label('total'),
            func.sum(
                case(
                    [(Report.status == 'Resolved', 1)],
                    else_=0
                )
            ).label('resolved')
        ).group_by(
            Report.location
        ).all()
        
        return {
            'top_locations': [{'location': l[0], 'count': l[1]} for l in top_locations],
            'location_resolution': [{
                'location': l[0],
                'total': l[1],
                'resolved': l[2],
                'rate': (l[2] / l[1] * 100) if l[1] > 0 else 0
            } for l in location_resolution]
        }

    @staticmethod
    def get_response_time_metrics():
        """Get metrics about response and resolution times"""
        try:
            # Check if the columns exist
            columns_exist = db.session.execute(text("""
                SELECT COUNT(*) FROM pragma_table_info('report') 
                WHERE name IN ('first_response_time', 'resolution_time')
            """)).scalar() == 2

            if not columns_exist:
                return {
                    'avg_response_time': 0,
                    'avg_resolution_time': 0
                }

            # Get average time to first response and resolution
            response_times = db.session.query(
                func.avg(
                    case(
                        [(Report.first_response_time != None, 
                          func.julianday(Report.first_response_time) - func.julianday(Report.timestamp))],
                        else_=None
                    )
                ).label('avg_response_time'),
                func.avg(
                    case(
                        [(Report.resolution_time != None,
                          func.julianday(Report.resolution_time) - func.julianday(Report.timestamp))],
                        else_=None
                    )
                ).label('avg_resolution_time')
            ).first()
            
            # Convert days to seconds
            avg_response_seconds = response_times[0] * 86400 if response_times and response_times[0] else 0
            avg_resolution_seconds = response_times[1] * 86400 if response_times and response_times[1] else 0
            
            return {
                'avg_response_time': avg_response_seconds,
                'avg_resolution_time': avg_resolution_seconds
            }
        except Exception as e:
            print(f"Error getting response time metrics: {e}")
            return {
                'avg_response_time': 0,
                'avg_resolution_time': 0
            }

@analytics.route('/analytics')
@login_required
def analytics_dashboard():
    if not current_user.is_authenticated:
        flash('Please log in to access the analytics dashboard.', 'error')
        return redirect(url_for('auth.login'))

    try:
        # Get report statistics
        stats = Analytics.get_report_stats()
        
        # Get trends data
        trends = Analytics.get_trends()
        
        # Format trends data safely
        trends_data = []
        for trend in trends['daily_counts']:
            if isinstance(trend['date'], datetime):
                formatted_date = trend['date'].strftime('%Y-%m-%d')
            else:
                formatted_date = str(trend['date'])
            trends_data.append({
                'date': formatted_date,
                'count': trend['count']
            })
        
        # Get status distribution
        status_distribution = [{
            'status': status[0] if status[0] else 'Unknown',
            'count': status[1] if status[1] is not None else 0
        } for status in trends['status_distribution']]
        
        # Get user activity
        user_activity = Analytics.get_user_activity()
        
        # Get location insights
        location_insights = Analytics.get_location_insights()
        
        # Get response time metrics
        response_metrics = Analytics.get_response_time_metrics()
        
        return render_template(
            'analytics.html',
            stats=stats,
            trends=trends_data,
            status_distribution=status_distribution,
            user_activity=user_activity,
            location_insights=location_insights,
            response_metrics=response_metrics,
            error=None
        )
        
    except Exception as e:
        return render_template(
            'analytics.html',
            stats={'total': 0, 'resolved': 0, 'pending': 0, 'in_progress': 0, 'resolution_rate': 0},
            trends=[],
            status_distribution=[],
            user_activity={'total_users': 0, 'active_users': 0, 'top_reporters': []},
            location_insights={'top_locations': [], 'resolution_by_location': []},
            response_metrics={'avg_first_response': None, 'avg_resolution_time': None},
            error=str(e)
        ) 