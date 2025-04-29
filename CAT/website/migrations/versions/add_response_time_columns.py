"""add response time columns

Revision ID: add_response_time_columns
Revises: 
Create Date: 2024-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_response_time_columns'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to report table
    op.add_column('report', sa.Column('first_response_time', sa.DateTime(), nullable=True))
    op.add_column('report', sa.Column('resolution_time', sa.DateTime(), nullable=True))
    op.add_column('report', sa.Column('last_updated', sa.DateTime(), nullable=True, default=datetime.utcnow))

def downgrade():
    # Remove the columns if we need to rollback
    op.drop_column('report', 'first_response_time')
    op.drop_column('report', 'resolution_time')
    op.drop_column('report', 'last_updated') 