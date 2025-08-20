import os
import tempfile
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supa import supabase, admin_client
import smtplib
from email.message import EmailMessage
import random
import string
# -------------------------
# CONFIG
# -------------------------
ADMIN_EMAIL = "automatexpos@gmail.com"
APP_EMAIL = "automatexpos@gmail.com"
APP_PASSWORD = "npul lior kqcv tvat"  # Gmail App Password

BOOK_WINDOW_MINUTES = 5
PK_TZ = timezone(timedelta(hours=5))  # Pakistan Standard Time

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')


# -------------------------
# HELPERS
# -------------------------
def send_email(subject, body, receipt=None, to_email=None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = APP_EMAIL
    msg['To'] = to_email or ADMIN_EMAIL   # fallback to admin if not specified
    msg.set_content(body)

    if receipt:
        file_data = receipt.read()
        receipt.seek(0)
        msg.add_attachment(file_data,
                           maintype='image',
                           subtype='jpeg',
                           filename=receipt.filename)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(APP_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)


def fetch_phones(category=None, sort=None, search=None, filter_status=None):
    query = supabase.table('phones').select('*')
    if filter_status:
        query = query.eq('status', filter_status)
    if category:
        query = query.eq('category', category)
    if search:
        query = query.ilike('model', f'%{search}%')
    if sort == 'price_asc':
        query = query.order('price', desc=False)
    elif sort == 'price_desc':
        query = query.order('price', desc=True)
    data = query.execute().data
    return data


@app.context_processor
def inject_now():
    return {'now': datetime.now}


@app.template_filter('format_dt')
def format_datetime(value):
    """Format ISO datetime string to m/d/Y h:mm AM/PM"""
    if not value:
        return ""
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return value
    elif isinstance(value, datetime):
        dt = value
    else:
        return value

    try:
        # Works on Linux/Mac
        return dt.strftime("%-m/%-d/%Y %-I:%M %p")
    except ValueError:
        # Works on Windows
        return dt.strftime("%#m/%#d/%Y %#I:%M %p")


def parse_datetime_fields(phones, fields=("booking_time","selling_time")):
    for p in phones:
        for f in fields:
            if p.get(f) and isinstance(p[f], str):
                try:
                    p[f] = datetime.fromisoformat(p[f].replace("Z","+00:00"))
                except Exception:
                    pass
    return phones

# -------------------------
# PUBLIC ROUTES
# -------------------------

# Admin: Mark a phone as sold
@app.route('/admin/mark_sold/<int:phone_id>', methods=['POST'])
def mark_sold(phone_id):
    supabase.table('phones').update({
        'status': 'Sold',
        'payment_status': 'Full paid'
    }).eq('id', phone_id).execute()
    
    flash('Phone marked as sold and payment set to Full paid!', 'ok')
    return redirect(url_for('admin_bookings'))

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'user_email' not in session:
        flash('You must be logged in to confirm payment.', 'error')
        return redirect(url_for('login'))

    cart_ids = request.args.get("cart_ids")
    phone_id = request.args.get("phone_id")

    phones, total_price, admin = [], 0, None

    # Single item
    if phone_id:
        res = supabase.table("phones").select("*, admin_id").eq("id", int(phone_id)).single().execute()
        phone = res.data
        if not phone:
            flash("Phone not found", "error")
            return redirect(url_for("home"))

        # fetch the admin who owns this phone
        admin = supabase.table("admins").select("*").eq("id", phone["admin_id"]).single().execute().data
        phones = [phone]
        total_price = float(phone["price"])

    # Multiple items from cart
    elif cart_ids:
        ids = [int(i) for i in cart_ids.split(",") if i]
        res = supabase.table("phones").select("*").in_("id", ids).execute()
        phones = res.data or []
        total_price = sum(float(p["price"]) for p in phones if p.get("price"))

        # ⚠️ For now assume all cart items belong to the same admin
        if phones:
            admin = supabase.table("admins").select("*").eq("id", phones[0]["admin_id"]).single().execute().data

    # -------------------------
    # GET → Show payment page
    # -------------------------
    if request.method == "GET":
        return render_template("payment.html", phones=phones, total_price=total_price, admin=admin)

    # -------------------------
    # POST → Handle payment form
    # -------------------------
    buyer_name = request.form["buyer_name"]
    buyer_email = request.form["buyer_email"]
    buyer_phone = request.form["buyer_phone"]
    buyer_address = request.form["buyer_address"]
    payment_method = request.form.get("payment_method")
    receipt = request.files.get("receipt")

    # -------------------------
    # Prepare email bodies
    # -------------------------
    subject = f"New Payment Confirmation - {buyer_name}"
    body = f"""
A customer has submitted a payment.

Name: {buyer_name}
Email: {buyer_email}
Phone: {buyer_phone}
Address: {buyer_address}

Items:
""" + "\n".join([f"- {p['model']} (Rs {p['price']})" for p in phones]) + f"""

Total Price: Rs {total_price}
Payment Method: {payment_method}
"""

    customer_body = f"""
Dear {buyer_name},

Thank you for your order! We have received your payment submission.  
Our team will review and confirm your payment shortly.

----------------------------------------
📦 Order Summary
----------------------------------------
""" + "\n".join([f"- {p['model']} (Rs {p['price']})" for p in phones]) + f"""

----------------------------------------
👤 Buyer Information
----------------------------------------
Name: {buyer_name}
Email: {buyer_email}
Phone: {buyer_phone}
Address: {buyer_address}

----------------------------------------
💳 Payment Details
----------------------------------------
Total Amount: Rs {total_price}
Payment Method: {payment_method}
Payment Status: Pending (awaiting admin confirmation)

We will notify you once your payment has been verified and your order is confirmed.  

Thank you for shopping with us!  
Automatexpo Team
"""

    # -------------------------
    # Send emails
    # -------------------------
    if admin:
        send_email(subject, body, receipt, to_email=admin["email"])   # notify seller admin
    else:
        send_email(subject, body, receipt, to_email=ADMIN_EMAIL)      # fallback

    send_email("Order Received", customer_body, to_email=buyer_email)

    # -------------------------
    # Update DB for all phones
    # -------------------------
    for p in phones:
        supabase.table("phones").update({
            "buyer_name": buyer_name,
            "buyer_email": buyer_email,
            "buyer_phone": buyer_phone,
            "buyer_address": buyer_address,
            "payment_method": payment_method,
            "payment_status": "Pending",
            "status": "Booked",
            "full_payment": True,
            "purchase_time": datetime.utcnow().isoformat(),
        }).eq("id", p["id"]).execute()

    flash("Purchase submitted. Admin will verify payment.", "ok")
    return redirect(url_for("account_purchased"))


@app.get('/')
def home():
    category = request.args.get('category')
    sort = request.args.get('sort')
    search = request.args.get('search')
    # Only fetch phones that are Available (not Sold or Booked)
    phones = fetch_phones(category=category, sort=sort, search=search, filter_status='Available')
    # Attach media to each phone
    for p in phones:
        p['media'] = supabase.table('phone_media').select('*').eq('phone_id', p['id']).execute().data
    return render_template('home.html', phones=phones)


@app.get('/phone/<int:phone_id>')
def phone_detail(phone_id):
    phone = supabase.table('phones').select('*').eq('id', phone_id).single().execute().data
    if not phone:
        flash('Phone not found', 'error')
        return redirect(url_for('home'))

    media = supabase.table('phone_media').select('*').eq('phone_id', phone_id).execute().data

    remaining_ms, deadline_iso = 0, None
    if phone['status'] == 'Booked' and phone.get('booking_time'):
        bt = datetime.fromisoformat(phone['booking_time'].replace('Z', '+00:00'))
        deadline = bt + timedelta(minutes=BOOK_WINDOW_MINUTES)
        now = datetime.now(timezone.utc)
        if deadline > now:
            remaining_ms = int((deadline - now).total_seconds() * 1000)
            deadline_iso = deadline.isoformat()

    return render_template('phone_detail.html', phone=phone, media=media,
                           remaining_ms=remaining_ms, deadline_iso=deadline_iso)


# -------------------------
# AUTH
# -------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    step = session.get("signup_step", "form")

    if request.method == 'POST':
        # STEP 1: Form submission → send OTP
        if step == "form":
            email = request.form['email']
            password = request.form['password']
            phone_field = request.form.get('phone')
            address = request.form.get('address')

            # Check if email already exists
            existing = supabase.table("profiles").select("id").eq("email", email).maybe_single().execute()
            if existing.data:
                flash("Email already registered. Please log in.", "danger")
                return redirect(url_for("login"))

            # Save data temporarily in session
            session['signup_email'] = email
            session['signup_password'] = password
            session['signup_phone'] = phone_field
            session['signup_address'] = address

            # Generate OTP
            otp = "".join(random.choices(string.digits, k=6))
            session['signup_otp'] = otp
            session['signup_step'] = "otp"

            # Send OTP to email
            subject = "Your Signup OTP"
            body = f"Your OTP code is: {otp}\n\nThis code will expire in 10 minutes."
            send_email(subject, body, to_email=email)

            flash("OTP has been sent to your email", "info")
            return render_template("signup_otp.html")

        # STEP 2: Verify OTP
        elif step == "otp":
            entered_otp = request.form.get("otp")
            if entered_otp == session.get("signup_otp"):
                try:
                    supabase.table('profiles').insert({
                        'email': session['signup_email'],
                        'password': session['signup_password'],
                        'phone': session['signup_phone'],
                        'address': session['signup_address'],
                        'role': 'customer'
                    }).execute()
                except Exception as e:
                    flash("Error creating account: " + str(e), "danger")
                    return redirect(url_for("signup"))

                # Clear session
                session.pop('signup_email', None)
                session.pop('signup_password', None)
                session.pop('signup_phone', None)
                session.pop('signup_address', None)
                session.pop('signup_otp', None)
                session['signup_step'] = "form"

                flash('Account created successfully. Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash("Invalid OTP", "danger")
                return render_template("signup_otp.html")

    # GET request → fresh signup form
    session['signup_step'] = "form"
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        res = supabase.table('profiles').select('*').eq('email', email).maybe_single().execute()
        user = res.data
        if user and user['password'] == password:
            session['user_email'] = email
            flash('Logged in.', 'ok')
            return redirect(url_for('home'))

        flash('Invalid credentials.', 'error')

    return render_template('login.html')


@app.get('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'ok')
    return redirect(url_for('home'))


@app.route("/reset", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        # Always reset state when user first visits reset page
        session["reset_step"] = "email"
        session.pop("reset_email", None)
        session.pop("reset_otp", None)

    step = session.get("reset_step", "email")

    if request.method == "POST":
        # STEP 1: User enters email → send OTP
        if step == "email":
            email = request.form.get("email")
            res = supabase.table("profiles").select("id").eq("email", email).single().execute()

            if res.data:
                # Generate OTP
                otp = "".join(random.choices(string.digits, k=6))
                session["reset_email"] = email
                session["reset_otp"] = otp
                session["reset_step"] = "otp"

                # Send OTP via email helper
                subject = "Your Password Reset OTP"
                body = f"Your OTP code is: {otp}\n\nThis code will expire in 10 minutes."
                send_email(subject, body, to_email=email)

                flash("OTP has been sent to your email", "info")
            else:
                flash("Email not found", "danger")

        # STEP 2: User enters OTP + new password
        elif step == "otp":
            otp = request.form.get("otp")
            new_password = request.form.get("new_password")
            email = session.get("reset_email")

            if otp == session.get("reset_otp"):
                # Lookup user ID from profiles
                profile = supabase.table("profiles").select("id").eq("email", email).single().execute()
                if profile.data:
                    # Just update password in profiles table
                    supabase.table("profiles").update({
                        "password": new_password
                    }).eq("email", email).execute()

                    flash("Password updated successfully. Please log in.", "success")


                    # Clear session state
                    session.pop("reset_email", None)
                    session.pop("reset_otp", None)
                    session["reset_step"] = "email"
                    return redirect(url_for("login"))
                else:
                    flash("User profile not found", "danger")
            else:
                flash("Invalid OTP", "danger")


    return render_template("reset.html", step=session.get("reset_step", "email"))


# -------------------------
# ACCOUNT
# -------------------------
@app.route('/account/booked')
def account_booked():
    if 'user_email' not in session:
        flash('You must be logged in to view your orders.', 'error')
        return redirect(url_for('login'))

    res = supabase.table('phones') \
        .select('*') \
        .eq('status', 'Booked') \
        .eq('buyer_email', session['user_email']) \
        .execute()

    phones = res.data or []
    phones = parse_datetime_fields(phones)   # <--- ADD THIS
    return render_template('account_booked.html', phones=phones)


@app.get('/account/purchased')
def account_purchased():
    if not session.get('user_email'):
        return redirect(url_for('login'))
    email = session['user_email']
    phones = supabase.table('phones').select('*') \
        .eq('buyer_email', email) \
        .in_('status', ['Booked', 'Sold']) \
        .execute().data
    phones = parse_datetime_fields(phones)

    return render_template('account_purchased.html', phones=phones)

# Initialize cart in session if not exists
def get_cart():
    if "cart" not in session:
        session["cart"] = []
    return session["cart"]

@app.route("/cart/add/<int:phone_id>", methods=["POST"])

def add_to_cart(phone_id):
    cart = get_cart()
    if phone_id not in cart:
        cart.append(phone_id)
        session["cart"] = cart
    return redirect(url_for("view_cart"))

@app.route("/cart")
def view_cart():
    cart_ids = get_cart()
    if not cart_ids:
        phones = []
        total_price = 0
    else:
        res = supabase.table("phones").select("*").in_("id", cart_ids).execute()
        phones = res.data
        # Calculate total
        total_price = sum(p["price"] for p in phones if "price" in p)

    return render_template("cart.html", phones=phones, total_price=total_price)


@app.route("/cart/clear", methods=["POST"])
def clear_cart():
    session.pop("cart", None)
    return redirect(url_for("view_cart"))



@app.route("/cart/checkout", methods=["POST"])
def checkout_cart():
    selected = request.form.getlist("selected_items")
    if not selected:
        flash("Please select at least one item.", "error")
        return redirect(url_for("view_cart"))

    # Redirect to payment with selected IDs
    return redirect(url_for("payment", cart_ids=",".join(selected)))


# -------------------------
# ADMIN AUTH
# -------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # could be email or username
        password = request.form.get('password')

        try:
            # Try to find by username OR email
            res = (
                supabase.table('admins')
                .select('*')
                .or_(f"username.eq.{identifier},email.eq.{identifier}")
                .maybe_single()
                .execute()
            )
        except Exception as e:
            flash('Database error: ' + str(e), 'error')
            return render_template('admin_login.html')

        admin = getattr(res, "data", None)

        if admin and admin.get('password') == password:
            session['is_admin'] = True
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            flash(f'Welcome, {admin["username"]}!', 'ok')
            return redirect(url_for('admin_items'))
        else:
            flash('Invalid admin credentials', 'error')

    return render_template('admin_login.html')


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)
    return wrapper

# -------------------------
# ADMIN ROUTES
# -------------------------

# Route for adding new phone
@app.route('/admin/items/new', methods=['GET', 'POST'])
@admin_required
def admin_item_new():
    if request.method == 'POST':
        model = request.form['model']
        specs = request.form['specs']
        condition = request.form['condition']
        price = float(request.form['price'])
        media_urls = request.form.get('media', '').strip().split('\n')
        category = request.form['category']

        # Insert phone
        phone_result = supabase.table("phones").insert({
            "model": model,
            "specs": specs,
            "condition": condition,
            "price": price,
            "status": "Available",
            "category": category,
            "admin_id": session["admin_id"]
        }).execute()
        
        phone_id = phone_result.data[0]['id']
        
        # Insert media
        for url in media_urls:
            if url.strip():
                supabase.table('phone_media').insert({
                    'phone_id': phone_id,
                    'url': url.strip(),
                    'kind': 'image'  # Default to image, you can enhance this later
                }).execute()
        
        flash('Phone added successfully!', 'ok')
        return redirect(url_for('admin_items'))


    categories = [c['cat_name'] for c in supabase.table('categories').select('cat_name').execute().data]
    categories = sorted(set(categories))  # Unique and sorted
    return render_template('admin_item_form.html', categories=categories, phone=None, media=[])

# Route for editing existing phone
@app.route('/admin/items/<int:phone_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_item_edit(phone_id):

    phone = supabase.table('phones').select('*').eq('id', phone_id).single().execute().data
    if not phone:
        flash('Phone not found', 'error')
        return redirect(url_for('admin_items'))

    # Prevent editing if sold
    if phone.get('status') == 'Sold':
        flash('Sold items cannot be edited.', 'error')
        return redirect(url_for('admin_items'))

    if request.method == 'POST':
        model = request.form['model']
        specs = request.form['specs']
        condition = request.form['condition']
        price = float(request.form['price'])
        media_urls = request.form.get('media', '').strip().split('\n')
        category = request.form['category']

        # Update phone
        supabase.table('phones').update({
            'model': model,
            'specs': specs,
            'condition': condition,
            "category": category,
            'price': price
        }).eq('id', phone_id).execute()
        
        # Delete existing media and add new ones
        supabase.table('phone_media').delete().eq('phone_id', phone_id).execute()
        
        # Insert new media
        for url in media_urls:
            if url.strip():
                supabase.table('phone_media').insert({
                    'phone_id': phone_id,
                    'url': url.strip(),
                    'kind': 'image'  # Default to image
                }).execute()
        
        flash('Phone updated successfully!', 'ok')
        return redirect(url_for('admin_items'))
       
    media = supabase.table('phone_media').select('*').eq('phone_id', phone_id).execute().data
    categories = [c['cat_name'] for c in supabase.table('categories').select('cat_name').execute().data]
    categories = sorted(set(categories))
    return render_template('admin_item_form.html', phone=phone, media=media, categories=categories)

# Route for reviewing phone (payment verification)
@app.route('/admin/review', methods=['GET', 'POST'])
@admin_required
def admin_review():
    phone_id = request.args.get('phone_id')
    phone = None
    
    if phone_id:
        phone = supabase.table('phones').select('*').eq('id', phone_id).single().execute().data
    
    # Get all pending bookings
    pending = supabase.table('phones').select('*').eq('status', 'Booked').order('booking_time', desc=True).execute().data
    
    return render_template('admin_review.html', phone=phone, pending=pending)


# Route for verifying payments from review page
@app.route('/admin/review/verify/<int:phone_id>', methods=['POST'])
@admin_required
def admin_review_verify(phone_id):
    action = request.form.get('action')
    phone = supabase.table('phones').select('*').eq('id', phone_id).single().execute().data

    if action == 'token':
        supabase.table('phones').update({
            'payment_status': 'Token paid'
        }).eq('id', phone_id).execute()
        flash('Token payment verified!', 'ok')
        
    elif action == 'full':
        now = datetime.now(timezone.utc).isoformat()
        supabase.table('phones').update({
            'payment_status': 'Full paid',
            'status': 'Sold',
            'selling_time': now,
            'shipping_status': 'Pending'
        }).eq('id', phone_id).execute()
        flash('Full payment verified and phone marked as sold!', 'ok')
        
    elif action == 'revert':
        if phone.get('status') == 'Sold':
            flash('Sold items cannot be reverted to available.', 'error')
            return redirect(url_for('admin_review'))
        
        supabase.table('phones').update({
            'status': 'Available',
            'buyer_email': None,
            'buyer_phone': None,
            'booking_time': None,
            'payment_status': None,
            'full_payment': False,
            'shipping_status': None,
            'tracking_number': None,
            'selling_time': None,
            'created_at': None,
            'updated_at': None,
            'tracking_number': None

        }).eq('id', phone_id).execute()
        flash('Phone reverted to available!', 'ok')
    
    return redirect(url_for('admin_review'))

@app.get('/admin/items')
@admin_required
def admin_items():
    phones = supabase.table('phones').select('*').eq('admin_id', session['admin_id']).execute().data
    return render_template('admin_items.html', phones=phones)

@app.post('/admin/items/<int:phone_id>/token')
@admin_required
def mark_token_received(phone_id):
    supabase.table("phones").update({"payment_status": "Token paid"}).eq("id", phone_id).execute()
    flash("Token marked as received.", "ok")
    return redirect(url_for("admin_bookings"))


@app.post('/admin/items/<int:phone_id>/full')
@admin_required
def mark_full_payment(phone_id):
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("phones").update({
        "payment_status": "Full paid",
        "status": "Sold",
        "selling_time": now,
        "shipping_status": "Pending"
    }).eq("id", phone_id).execute()

    # ✅ This is where we fetch updated phone info
    phone = supabase.table("phones").select("*").eq("id", phone_id).single().execute().data

    # ✅ Build the invoice-style email body here
    subject = f"Order Confirmation - Phone Purchase #{phone['id']}"
    body = f"""
Dear {phone.get('buyer_name', 'Customer')},

Thank you for your purchase! Your order has been confirmed and marked as fully paid.  
Here are your order details:

----------------------------------------
📦 Order Summary
----------------------------------------
Model: {phone['model']}
Condition: {phone['condition']}
Price: Rs {phone['price']}

----------------------------------------
👤 Buyer Information
----------------------------------------
Name: {phone.get('buyer_name')}
Email: {phone.get('buyer_email')}
Phone: {phone.get('buyer_phone')}
Address: {phone.get('buyer_address')}

----------------------------------------
💳 Payment Details
----------------------------------------
Payment Status: {phone.get('payment_status')}
Order ID: {phone['id']}
Selling Date: {phone.get('selling_time', '')}

----------------------------------------
🚚 Shipping Status
----------------------------------------
{phone.get('shipping_status', 'Pending')}

We will share tracking information with you as soon as your order is shipped.  
If you have any questions, feel free to reply to this email.

Thank you for shopping with us!  
Automatexpo Team
"""

    # ✅ Send email to customer
    if phone.get("buyer_email"):
        send_email(subject, body, to_email=phone["buyer_email"])

    flash("Full payment received & phone marked as Sold.", "ok")
    return redirect(url_for("admin_bookings"))


@app.post('/admin/items/<int:phone_id>/ship')
@admin_required
def mark_shipped(phone_id):
    tracking_number = request.form.get('tracking_number')
    if not tracking_number:
        flash("Tracking number is required to mark as shipped!", "error")
        return redirect(url_for('admin_bookings'))

    # Update DB
    res = supabase.table('phones').update({
        'shipping_status': 'Shipped',
        'tracking_number': tracking_number
    }).eq('id', phone_id).execute()

    # Fetch phone + buyer details
    phone = supabase.table("phones").select("*").eq("id", phone_id).single().execute().data

    if phone and phone.get("buyer_email"):
        buyer_email = phone["buyer_email"]
        buyer_name = phone.get("buyer_name", "Customer")

        subject = "📦 Your order has been shipped!"
        body = f"""
Dear {buyer_name},

Good news! Your order has been shipped. 🎉

----------------------------------------
📱 Item: {phone.get("model")}
💵 Price: Rs {phone.get("price")}
----------------------------------------

🚚 Shipping Status: Shipped  
📦 Tracking Number: {tracking_number}

You can use this tracking number to follow your shipment’s progress.

Thank you for shopping with us!
Automatexpo Team
"""

        # Send to buyer
        send_email(subject, body, to_email=buyer_email)

    flash(f'Phone {phone_id} marked as Shipped with tracking number {tracking_number}', 'ok')
    return redirect(url_for('admin_bookings'))



@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    pending = supabase.table('phones').select('*') \
        .eq('status', 'Booked') \
        .eq('payment_status', 'Pending') \
        .eq('admin_id', session['admin_id']) \
        .order('purchase_time', desc=True) \
        .execute().data

    sold = supabase.table('phones').select('*') \
        .eq('status', 'Sold') \
        .eq('admin_id', session['admin_id']) \
        .order('selling_time', desc=True) \
        .execute().data

    pending = parse_datetime_fields(pending, fields=("purchase_time",))
    sold = parse_datetime_fields(sold, fields=("selling_time",))

    return render_template('admin_bookings.html', pending=pending, sold=sold)


@app.get('/admin/sold')
@admin_required
def admin_sold():
    sold = supabase.table('phones').select('*') \
        .eq('status','Sold') \
        .order('selling_time', desc=True) \
        .execute().data or []

    sold = parse_datetime_fields(sold)   # <-- format dates properly

    return render_template('admin_sold.html', sold=sold)


# -------------------------
# MAIN
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
