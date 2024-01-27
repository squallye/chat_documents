import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, MetaData,Table,JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from alembic import op
import sqlalchemy as sa


db_connection_string = "mysql+pymysql://klj5c8sk8y0si1uwcffg:pscale_pw_T1QdxikDMJscilfg4t4Q1Jkmu5FUS26fhggLIAvWOp1@aws.connect.psdb.cloud/flask_test_database?charset=utf8mb4"

engine = create_engine(
    db_connection_string,
    connect_args={
        "ssl":{
            "ssl_ca": "/etc/ssl/cert.pem"
        }
    })

  
table_name = 'users'
  
def upgrade():
    op.add_column('table_name', sa.Column('new_column_name', sa.String(50)))



