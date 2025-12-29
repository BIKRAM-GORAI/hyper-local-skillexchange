# from app import app, db, service_request
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
db = SQLAlchemy(app)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)