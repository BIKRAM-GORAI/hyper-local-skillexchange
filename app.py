# from app import app, db, service_request
from flask import Flask, request, render_template, redirect, url_for,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
db = SQLAlchemy(app)

class users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius_km = db.Column(db.Float, default=5.0)
    is_provider = db.Column(db.Boolean, default=False)
    is_consumer = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        fullname = request.form['fullname']
        role = request.form['role']
        lat = request.form['latitude']
        lng = request.form['longitude']
        password_hash = generate_password_hash(password)
        is_provider = role == 'provider'
        is_consumer = role == 'consumer'

        new_user = users(
            email=email,
            password_hash=password_hash,
            full_name=fullname,
            latitude=float(lat),
            longitude=float(lng),
            is_provider=is_provider,
            is_consumer=is_consumer,
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)