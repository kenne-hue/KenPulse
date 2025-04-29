from website import create_app, db
from website.models import Report
from sqlalchemy import text

def migrate_database():
    app = create_app()
    with app.app_context():
        try:
            # Create a new table with the updated schema
            db.session.execute(text("""
                CREATE TABLE report_new (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL,
                    location VARCHAR(100) NOT NULL,
                    latitude FLOAT,
                    longitude FLOAT,
                    status VARCHAR(20) DEFAULT 'Pending',
                    timestamp DATETIME,
                    user_id INTEGER,
                    image_url VARCHAR(200),
                    resolution_proof VARCHAR(200),
                    resolution_description TEXT,
                    proof_verified BOOLEAN DEFAULT 0,
                    first_response_time DATETIME,
                    resolution_time DATETIME,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user (id)
                )
            """))
            
            # Copy data from old table to new table
            db.session.execute(text("""
                INSERT INTO report_new (
                    id, title, description, location, latitude, longitude,
                    status, timestamp, user_id, image_url, resolution_proof,
                    resolution_description, proof_verified
                )
                SELECT 
                    id, title, description, location, latitude, longitude,
                    status, timestamp, user_id, image_url, resolution_proof,
                    resolution_description, proof_verified
                FROM report
            """))
            
            # Drop the old table
            db.session.execute(text("DROP TABLE report"))
            
            # Rename the new table to the original name
            db.session.execute(text("ALTER TABLE report_new RENAME TO report"))
            
            db.session.commit()
            print("Successfully migrated the database")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {e}")
            raise

if __name__ == '__main__':
    migrate_database() 