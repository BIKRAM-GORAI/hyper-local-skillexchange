# from app import app, db, service_request
import os
from flask import Flask, request, render_template, redirect, url_for, session, g, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from math import radians, cos, sin, asin, sqrt
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix Render postgres:// issue
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL:
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/mydatabase.db"

db = SQLAlchemy(app)

app.secret_key = os.getenv("SECRET_KEY")






# 1. Define the distance calculation function (Haversine Formula)
def calculate_distance(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]:
        return 99999 # Return a huge distance if data is missing
    
    # Convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers
    return c * r

# 2. Register it so Jinja can use it
app.jinja_env.globals.update(distance_km=calculate_distance)

class users(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)

    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    radius_km = db.Column(db.Float, default=5.0)  # optional usage

    is_provider = db.Column(db.Boolean, default=False)
    is_consumer = db.Column(db.Boolean, default=False)
    user_skill=db.Column(db.String(20), nullable=True)
    # is_admin = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class service_request(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    consumer_id=db.Column(db.Integer, nullable=False)
    con_latitude = db.Column(db.Float, nullable=False)
    con_longitude = db.Column(db.Float, nullable=False)
    service_title=db.Column(db.String(200), nullable=False)
    service_type=db.Column(db.String(50), nullable=False)
    budget=db.Column(db.Integer, nullable=False)
    desc=db.Column(db.String(500), nullable=False)
    is_active=db.Column(db.Boolean, default=True)
    is_inprogress=db.Column(db.Boolean, default=False)
    assigned_provider_id=db.Column(db.Integer, nullable=True)
    created_at=db.Column(db.DateTime, default=db.func.current_timestamp())


class bids(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    bid_amount=db.Column(db.Integer, nullable=False)
    ser_req_id=db.Column(db.Integer, nullable=False)
    con_id=db.Column(db.Integer, nullable=False)
    prov_id=db.Column(db.Integer, nullable=False)
    msg=db.Column(db.String(500), nullable=False)


class reviews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    req_id = db.Column(db.Integer, nullable=False)
    consumer_id = db.Column(db.Integer, nullable=False)
    provider_id = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Integer, nullable=False) 
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


@app.route('/', methods=['GET', 'POST'])#login
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = users.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Logged in successfully!')
            #print('login suck')
            # print(user.id)
            # print(session['user_id'])
            if user.is_consumer==True:
                #print('consumer')
                return redirect(url_for('consumer_dashboard'))  # Redirect to home/dashboard; adjust as needed
            else:
                return redirect(url_for('provider_dashboard'))
        else:
            flash('Invalid email or password.')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])#signup
def register():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        fullname = request.form['fullname']
        # address = request.form['address']
        role = request.form['role']
        lat = request.form['latitude']
        lng = request.form['longitude']
        skill=request.form.get('service_type')
        #print("Skill:",skill)
        # Hash the password
        password_hash = generate_password_hash(password)

        # Determine roles
        is_provider = role == 'provider'
        is_consumer = role == 'consumer'
        # is_admin = email == admin_email

        # Create new user
        new_user = users(
            email=email,
            password_hash=password_hash,
            full_name=fullname,
            latitude=float(lat),
            longitude=float(lng),
            is_provider=is_provider,
            is_consumer=is_consumer,
            user_skill=skill
            # is_admin=is_admin
        )

        # Add to database
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('auth/register.html')

@app.route('/consumer_dashboard')
def consumer_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    id=session['user_id']
    #print(id)
    current_user_object = users.query.get(id)
    ser_req=service_request.query.filter_by(consumer_id=id).all()
    # print(ser_req)
    # print(ser_req[0].service_title,ser_req[0].service_type)
    active_req_ids = [r.id for r in ser_req if r.is_active] 
    
    requests_with_bids = []
    if active_req_ids:
        # Query bids only for these ACTIVE requests
        active_bids_query = db.session.query(bids.ser_req_id)\
                        .filter(bids.ser_req_id.in_(active_req_ids))\
                        .distinct().all()
        
        requests_with_bids = [r[0] for r in active_bids_query]
    #print("count: ",len(ser_req),ser_req)
    return render_template('consumer/consumer_dashboard.html',user=current_user_object,requests=ser_req,requests_with_bids=requests_with_bids)

@app.route('/add_requests',methods=['GET', 'POST'])
def add_service_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    id=session['user_id']
    con_user = users.query.get(id)
    consumer_id=con_user.id
    if request.method == "POST":
        service_title = request.form['service_title']
        service_type=request.form['service_type']
        service_desc = request.form['service_desc']
        budget = request.form['budget']
        lat=request.form['latitude']
        long=request.form['longitude']
        
        
        new_service_request = service_request(
            service_title=service_title,
            service_type=service_type,
            budget=budget,
            desc=service_desc,
            consumer_id=consumer_id,
            con_latitude = lat,
            con_longitude=long
        )

        # Add to database
        db.session.add(new_service_request)
        db.session.commit()

        flash('Service Added Successfully')
        return redirect(url_for('consumer_dashboard'))
    return render_template('consumer/service_request.html')

from sqlalchemy.sql import func # Import this at the top

@app.route('/view_bids/<int:req_id>')
def view_bids(req_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    req = service_request.query.get_or_404(req_id)
    if req.consumer_id != session['user_id']:
        flash("Unauthorized")
        return redirect(url_for('consumer_dashboard'))

    # Fetch Bids and Providers
    results = db.session.query(bids, users).join(users, bids.prov_id == users.id).filter(bids.ser_req_id == req_id).all()
    
    # NEW: Calculate Stats for each Provider in the list
    provider_stats = {} 
    
    for bid, provider in results:
        # 1. Count completed jobs (where they were assigned and it is not active/inprogress)
        # Note: Depending on your logic, you might just count rows in the 'reviews' table for confirmed completions
        job_count = reviews.query.filter_by(provider_id=provider.id).count()
        
        # 2. Calculate Average Rating
        avg_rating_query = db.session.query(func.avg(reviews.rating)).filter(reviews.provider_id == provider.id).scalar()
        avg_rating = round(avg_rating_query, 1) if avg_rating_query else 0
        
        provider_stats[provider.id] = {
            'count': job_count,
            'rating': avg_rating
        }
    
    return render_template('consumer/view_bids.html', service=req, bid_data=results, stats=provider_stats)

@app.route('/accept_bid/<int:bid_id>')
def accept_bid(bid_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 1. Get the bid
    winning_bid = bids.query.get_or_404(bid_id)
    
    # 2. Get the related service request
    req = service_request.query.get(winning_bid.ser_req_id)

    # Security check
    if req.consumer_id != session['user_id']:
        flash("Unauthorized action.")
        return redirect(url_for('consumer_dashboard'))

    # 3. Update the Service Request
    req.assigned_provider_id = winning_bid.prov_id
    req.is_active = False       # Remove from the "Available" pool for other providers
    req.is_inprogress = True    # Mark as ongoing
    
    # 4. (Optional) You might want to update the budget to the final agreed bid amount
    # req.budget = winning_bid.bid_amount 

    db.session.commit()
    
    flash(f'Bid accepted! Provider ID {winning_bid.prov_id} has been assigned.')
    return redirect(url_for('consumer_dashboard'))


@app.route('/my_orders')
def my_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    con_id = session['user_id']
    
    # Fetch requests created by this consumer that are EITHER active OR in progress
    # We join with 'users' (provider) to show who is doing the work
    # We use an outer join (isouter=True) because some requests might not have a provider yet
    
    orders = db.session.query(service_request, users).outerjoin(users, service_request.assigned_provider_id == users.id)\
        .filter(service_request.consumer_id == con_id).all()
        
    return render_template('consumer/my_orders.html', orders=orders)

@app.route('/close_order/<int:req_id>', methods=['GET', 'POST'])
def close_order(req_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    req = service_request.query.get_or_404(req_id)
    
    # Check if form is submitted (The Review)
    if request.method == "POST":
        rating = int(request.form['rating'])
        comment = request.form['comment']
        
        # 1. Create Review
        new_review = reviews(
            req_id=req.id,
            consumer_id=session['user_id'],
            provider_id=req.assigned_provider_id,
            rating=rating,
            comment=comment
        )
        db.session.add(new_review)
        
        # 2. Close the Order
        req.is_inprogress = False
        req.is_active = False
        
        db.session.commit()
        
        flash("Job completed and review submitted!")
        return redirect(url_for('my_orders'))

    # If GET request, show the Review Page
    # Pass the provider name so we can say "How was your experience with X?"
    provider = users.query.get(req.assigned_provider_id)
    return render_template('consumer/leave_review.html', req=req, provider=provider)

@app.route('/provider_dashboard')
def provider_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    id=session['user_id']
    #print("id:",id)
    current_user_object = users.query.get(id)
    #print(current_user_object.user_skill)
    ser_req=service_request.query.filter_by(service_type=current_user_object.user_skill)
    # print(ser_req)
    # print(ser_req[0].service_type,ser_req[1].service_type)
    # print(ser_req[0].service_title,ser_req[0].service_type)
    # print(current_user_object.user_skill,ser_req[0].service_type)
    # print(calculate_distance(ser_req[0].con_latitude,ser_req[0].con_longitude,current_user_object.latitude,current_user_object.longitude))
    my_bids=bids.query.filter_by(prov_id=id).all()

    bid_request_ids=[bid.ser_req_id for bid in my_bids]
    return render_template('provider/provider_dashboard.html',user=current_user_object,requests=ser_req,bid_request_ids=bid_request_ids)

@app.route('/place_bid/<int:serv_id>',methods=['GET', 'POST'])
def place_bid(serv_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == "POST":
        bid_amount = request.form['bid_amount']
        msg = request.form['msg']
        ser_req_id = serv_id
        service = service_request.query.filter_by(id=serv_id).first()
        con_id = service.consumer_id
        prov_id = session['user_id']
        
        new_bid = bids(
            bid_amount=bid_amount,
            ser_req_id=ser_req_id,
            con_id=con_id,
            prov_id=prov_id,
            msg=msg
        )

        # Add to database
        db.session.add(new_bid)
        db.session.commit()

        flash('Bid placed successfully!')
        return redirect(url_for('provider_dashboard'))
    

    service=service_request.query.filter_by(id=serv_id).first()
    return render_template('provider/place_bid.html',service=service)

@app.route('/edit_bid/<int:serv_id>', methods=['GET', 'POST'])
def edit_bid(serv_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    prov_id = session['user_id']
    
    # 1. Fetch the specific bid made by this provider for this service request
    current_bid = bids.query.filter_by(ser_req_id=serv_id, prov_id=prov_id).first()
    
    # Safety check: if bid doesn't exist, send them back
    if not current_bid:
        flash("Bid not found.")
        return redirect(url_for('provider_dashboard'))

    # 2. Fetch service details (just to show the title/budget to the user again)
    service = service_request.query.get(serv_id)

    # 3. Handle Form Submission (POST)
    if request.method == 'POST':
        current_bid.bid_amount = request.form['bid_amount']
        current_bid.msg = request.form['msg']
        
        db.session.commit() # Save changes to the existing record
        
        flash('Bid updated successfully!')
        return redirect(url_for('provider_dashboard'))

    # 4. Handle Page Load (GET) - Pass 'current_bid' to pre-fill the form
    return render_template('provider/edit_bid.html', service=service, bid=current_bid)

@app.route('/my_works')
def my_works():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    prov_id = session['user_id']
    
    # Fetch requests where this provider is the 'assigned_provider_id'
    # We join with 'users' to get the Consumer's name and email
    jobs = db.session.query(service_request, users).join(users, service_request.consumer_id == users.id)\
        .filter(service_request.assigned_provider_id == prov_id)\
        .filter(service_request.is_inprogress == True).all() 
        
    return render_template('provider/my_works.html', jobs=jobs)


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('login'))


# name
# email
# password
# role
# location
# lat lon rad
# skills
# repu
# completed jobs



# ---service req
# service ticket no
# title
# desc
# service type
# budget
# cus id
# status
# provider id
# review given
# rating given



# ---review model


# with app.app_context():
#     users.__table__.drop(db.engine)
#     print("Table dropped successfully.")

# with app.app_context():
#     service_request.__table__.drop(db.engine)
#     print("Table dropped successfully.")





if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run()