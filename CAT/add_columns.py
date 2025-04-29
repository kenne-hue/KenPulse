from website import create_app, db
from website.models import Report

def add_columns():
    app = create_app()
    with app.app_context():
        # Check if columns exist
        columns_exist = db.session.execute(
            db.text("""
            SELECT COUNT(*) FROM pragma_table_info('report') 
            WHERE name IN ('first_response_time', 'resolution_time', 'last_updated')
            """)
        ).scalar() == 3

        if not columns_exist:
            # Add new columns
            db.session.execute(db.text("""
                ALTER TABLE report ADD COLUMN first_response_time DATETIME;
                ALTER TABLE report ADD COLUMN resolution_time DATETIME;
                ALTER TABLE report ADD COLUMN last_updated DATETIME DEFAULT CURRENT_TIMESTAMP;
            """))
            db.session.commit()
            print("Successfully added new columns to the report table")
        else:
            print("Columns already exist")

if __name__ == '__main__':
    add_columns() 