from flask import Blueprint, render_template
from flask_login import login_required, current_user
from website.models import Report, User
from website import db
from sqlalchemy import func, case, cast, Float
from datetime import datetime, timedelta

analytics = Blueprint('analytics', __name__)

@analytics.route('/analytics')
@login_required
def analytics_dashboard():
    try:
        # Get report statistics
        stats = {
            'total': Report.query.count() or 0,
            'resolved': Report.query.filter_by(status='Resolved').count() or 0,
            'pending': Report.query.filter_by(status='Pending').count() or 0,
            'in_progress': Report.query.filter_by(status='In Progress').count() or 0,
        }
        
        # Calculate resolution rate safely
        stats['resolution_rate'] = int((stats['resolved'] / stats['total'] * 100) if stats['total'] > 0 else 0)

        # Get trends over last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        trends_query = db.session.query(
            func.date(Report.timestamp).label('date'),
            func.count(Report.id).label('count')
        ).filter(
            Report.timestamp >= thirty_days_ago
        ).group_by(
            func.date(Report.timestamp)
        ).all()
        
        # Format trends data safely
        trends_data = []
        for trend in trends_query:
            try:
                date = trend.date.strftime('%Y-%m-%d') if trend.date else ''
                count = trend.count if trend.count is not None else 0
                trends_data.append({'date': date, 'count': count})
            except (AttributeError, IndexError):
                continue

        # Get status distribution
        status_query = db.session.query(
            Report.status,
            func.count(Report.id).label('count')
        ).group_by(Report.status).all()
        
        # Format status distribution data safely
        status_data = []
        for status in status_query:
            try:
                status_name = status[0] if status[0] else 'Unknown'
                count = status[1] if status[1] is not None else 0
                status_data.append({'status': status_name, 'count': count})
            except (AttributeError, IndexError):
                continue

        # Get user activity
        user_activity = {
            'total_users': User.query.count() or 0,
            'active_users': User.query.filter(User.last_login >= thirty_days_ago).count() or 0,
            'top_reporters': []
        }

        # Get top reporters safely
        top_reporters_query = db.session.query(
            User.first_name,
            User.last_name,
            func.count(Report.id).label('report_count')
        ).join(Report).group_by(User.id).order_by(func.count(Report.id).desc()).limit(5).all()
        
        for reporter in top_reporters_query:
            try:
                first_name = reporter[0] if reporter[0] else ''
                last_name = reporter[1] if reporter[1] else ''
                report_count = reporter[2] if reporter[2] is not None else 0
                user_activity['top_reporters'].append({
                    'first_name': first_name,
                    'last_name': last_name,
                    'report_count': report_count
                })
            except (AttributeError, IndexError):
                continue

        # Get location insights
        location_insights = {
            'top_locations': [],
            'resolution_by_location': []
        }

        # Get top locations safely
        top_locations_query = db.session.query(
            Report.location,
            func.count(Report.id).label('count')
        ).group_by(Report.location).order_by(func.count(Report.id).desc()).limit(5).all()
        
        for location in top_locations_query:
            try:
                loc = location[0] if location[0] else 'Unknown'
                count = location[1] if location[1] is not None else 0
                location_insights['top_locations'].append({
                    'location': loc,
                    'count': count
                })
            except (AttributeError, IndexError):
                continue

        # Get resolution rates by location safely
        resolution_rates_query = db.session.query(
            Report.location,
            cast(
                func.avg(
                    case(
                        [(Report.status == 'Resolved', 1)],
                        else_=0
                    )
                ) * 100,
                Float
            ).label('resolution_rate')
        ).group_by(Report.location).all()
        
        for rate in resolution_rates_query:
            try:
                loc = rate[0] if rate[0] else 'Unknown'
                resolution_rate = float(rate[1]) if rate[1] is not None else 0.0
                location_insights['resolution_by_location'].append({
                    'location': loc,
                    'resolution_rate': resolution_rate
                })
            except (AttributeError, IndexError, ValueError):
                continue

        # Get response time metrics
        response_metrics = {
            'avg_first_response': None,
            'avg_resolution_time': None
        }

        # Calculate average first response time safely
        avg_first_response = db.session.query(
            func.avg(
                case(
                    [(Report.first_response_time.isnot(None),
                      func.julianday(Report.first_response_time) - func.julianday(Report.timestamp))],
                    else_=None
                )
            )
        ).scalar()

        if avg_first_response is not None:
            response_metrics['avg_first_response'] = avg_first_response * 86400  # Convert days to seconds

        # Calculate average resolution time safely
        avg_resolution_time = db.session.query(
            func.avg(
                case(
                    [(Report.resolution_time.isnot(None),
                      func.julianday(Report.resolution_time) - func.julianday(Report.timestamp))],
                    else_=None
                )
            )
        ).scalar()

        if avg_resolution_time is not None:
            response_metrics['avg_resolution_time'] = avg_resolution_time * 86400  # Convert days to seconds

        return render_template('analytics.html',
                             user=current_user,
                             stats=stats,
                             trends=trends_data,
                             status_distribution=status_data,
                             user_activity=user_activity,
                             location_insights=location_insights,
                             response_metrics=response_metrics)

    except Exception as e:
        return render_template('analytics.html',
                             user=current_user,
                             error=str(e)) 