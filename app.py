from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from flask_mail import Mail, Message
import os
import urllib.parse
import bcrypt

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)
app.secret_key = os.urandom(24)  # Secure secret key
# ==================== JINJA2 CUSTOM FILTER ====================
@app.template_filter('basename')
def jinja_basename(path):
    try:
        return basename(path)
    except:
        return path

# ==================== বাকি কোড (আগের মতোই) ====================
# ... তোমার বাকি সব কোড এখানে থাকবে ...
# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'samiulsk400@gmail.com'
app.config['MAIL_PASSWORD'] = 'endf zutt vasj lore'  # Replace with your app password
mail = Mail(app)

# Google Maps Location
GARAGE_LOCATION = "Mangalbari Malda, West Bengal Pin-732142"
GOOGLE_MAPS_LINK = "https://www.google.com/maps/place/Mangalbari+Rd,+Mangalbari,+West+Bengal+732101/@25.0198909,88.1499983,3a,75y,279.71h,97.37t/data=!3m7!1e1!3m5!1sbz_XQWOBS0QdusLu0NHZXg!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fcb_client%3Dmaps_sv.tactile%26w%3D900%26h%3D600%26pitch%3D-7.367948265855091%26panoid%3Dbz_XQWOBS0QdusLu0NHZXg%26yaw%3D279.71112116007146!7i13312!8i6656!4m15!1m8!3m7!1s0x39fafd964ea5afff:0xd12c8bc80b3b6642!2sMangalbari+Rd,+Mangalbari,+West+Bengal+732101!3b1!8m2!3d25.0199071!4d88.1500884!16s%2Fg%2F11c644_jt7!3m5!1s0x39fafd964ea5afff:0xd12c8bc80b3b6642!8m2!3d25.0199071!4d88.1500884!16s%2Fg%2F11c644_jt7?entry=ttu&g_ep=EgoyMDI1MDUwNy4wIKXMDSoJLDEwMjExNDUzSAFQAw%3D%3D"

# Database Setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        name TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bike_model TEXT,
        service_type TEXT,
        date TEXT,
        shop_number TEXT,
        status TEXT DEFAULT 'Pending',
        track_link TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        booking_id INTEGER,
        rating INTEGER,
        comment TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (booking_id) REFERENCES bookings (id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    # Insert default admin with hashed password
    hashed_admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    c.execute("INSERT OR IGNORE INTO admins (username, password) VALUES (?, ?)", ('admin', hashed_admin_password))
    conn.commit()
    conn.close()

init_db()

# Flask-Login User Class
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

# ==================== PDF GENERATION ====================
def generate_pdf(booking_id, username, bike_model, service_type, date, shop_number, track_link):
    pdf_dir = "static/pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_name = os.path.join(pdf_dir, f"booking_{booking_id}.pdf")

    c = canvas.Canvas(pdf_name, pagesize=letter)
    width, height = letter

    # Logo
    try:
        c.drawImage(ImageReader("static/images/samiul.png"), 200, 680, width=200, height=110)
    except:
        pass

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, 640, "SAMIUL MOTO GARAGE")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, 615, GARAGE_LOCATION)

    c.setLineWidth(2)
    c.line(80, 580, 520, 580)

    y = 550
    c.setFont("Helvetica-Bold", 12)
    for detail in [
        f"Booking ID     : {booking_id}",
        f"Customer       : {username}",
        f"Bike Model     : {bike_model}",
        f"Service        : {service_type}",
        f"Date           : {date}",
        f"Shop Number    : {shop_number}",
        f"Track Link     : {track_link}"
    ]:
        c.drawString(90, y, detail)
        y -= 30

    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width/2, 160, "Thank you for choosing Samiul Moto Garage!")
    c.drawCentredString(width/2, 140, "Contact: +91 9933924274")
    c.save()
    return pdf_name

# Email Sending Function
def send_confirmation_email(email, username, bike_model, service_type, date, shop_number, track_link, pdf_file, booking_id):
    msg = Message('Booking Confirmation - Samiul Moto Garage',
                  sender='samiulsk400@gmail.com',
                  recipients=[email])
    msg.body = f"""
    Dear {username},

    Your booking has been confirmed!
    Booking ID: {booking_id}
    Bike Model: {bike_model}
    Service Type: {service_type}
    Date: {date}
    Shop Number: {shop_number}
    Track Your Booking: {track_link}
    Garage Location: {GARAGE_LOCATION}
    Google Maps: {GOOGLE_MAPS_LINK}

    Please find the booking receipt attached.

    Thank you for choosing us!
    """
    with app.open_resource(pdf_file) as fp:
        msg.attach(f"booking_{booking_id}.pdf", "application/pdf", fp.read())
    mail.send(msg)

# WhatsApp Message Function
def send_whatsapp_message(phone, booking_id, username, bike_model, service_type, date, shop_number, status, pdf_file, track_link):
    message = f"""
    Dear {username},

    Your booking has been completed at Samiul Moto Garage:
    Booking ID: {booking_id}
    Bike Model: {bike_model}
    Service Type: {service_type}
    Date: {date}
    Shop Number: {shop_number}
    Status: {status}
    Track Link: {track_link}
    Garage Location: {GARAGE_LOCATION}
    Google Maps: {GOOGLE_MAPS_LINK}

    Download your booking receipt: http://127.0.0.1:5000/download/{urllib.parse.quote(pdf_file)}

    Thank you for choosing us!
    """
    encoded_message = urllib.parse.quote(message)
    whatsapp_url = f"https://wa.me/{phone}?text={encoded_message}"
    return whatsapp_url

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        phone = request.form['phone']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, email, name, phone) VALUES (?, ?, ?, ?, ?)",
                      (username, hashed_password, email, name, phone))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists!', 'error')
        conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            user_obj = User(user[0], user[1], user[3])
            login_user(user_obj)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, bike_model, service_type, date, shop_number, status, track_link FROM bookings WHERE user_id = ?", (current_user.id,))
    bookings = c.fetchall()
    conn.close()
    bookings = [dict(id=row[0], bike_model=row[1], service_type=row[2], date=row[3], shop_number=row[4], status=row[5], track_link=row[6]) for row in bookings]
    return render_template('dashboard.html', bookings=bookings)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, current_user.id))
        conn.commit()
        conn.close()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name, phone, email FROM users WHERE id = ?", (current_user.id,))
    user = c.fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    if request.method == 'POST':
        bike_model = request.form['bike_model']
        service_type = request.form['service_type']
        date = request.form['date']
        shop_number = "SHOP-" + str(datetime.now().strftime("%Y%m%d%H%M%S"))
        track_link = f"http://127.0.0.1:5000/track/{shop_number}"

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO bookings (user_id, bike_model, service_type, date, shop_number, track_link) VALUES (?, ?, ?, ?, ?, ?)",
                  (current_user.id, bike_model, service_type, date, shop_number, track_link))
        conn.commit()
        booking_id = c.lastrowid

        # Fetch user details for notifications
        c.execute("SELECT phone, username FROM users WHERE id = ?", (current_user.id,))
        user = c.fetchone()
        conn.close()

        # Generate PDF
        pdf_file = generate_pdf(booking_id, current_user.username, bike_model, service_type, date, shop_number, track_link)

        # Send email confirmation
        send_confirmation_email(current_user.email, current_user.username, bike_model, service_type, date, shop_number, track_link, pdf_file, booking_id)

        # Send WhatsApp message if phone number exists
        whatsapp_url = None
        if user and user[0]:
            whatsapp_url = send_whatsapp_message(user[0], booking_id, user[1], bike_model, service_type, date, shop_number, "Pending", pdf_file, track_link)
            flash('Booking completed! A confirmation has been sent via email and WhatsApp.', 'success')
        else:
            flash('Booking completed! A confirmation has been sent via email. Please add your phone number to receive WhatsApp notifications.', 'success')

        return render_template('booking_confirmation.html', pdf_file=pdf_file, shop_number=shop_number, booking_id=booking_id, bike_model=bike_model, service_type=service_type, date=date, track_link=track_link, whatsapp_url=whatsapp_url, google_maps_link=GOOGLE_MAPS_LINK)
    return render_template('booking.html')

@app.route('/download/<filename>')
def download_pdf(filename):
    return send_file(f"static/pdfs/{filename}", as_attachment=True)

@app.route('/track/<shop_number>')
def track(shop_number):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, bike_model, service_type, date, shop_number, status, track_link FROM bookings WHERE shop_number = ?", (shop_number,))
    booking = c.fetchone()
    conn.close()
    if booking:
        booking = dict(id=booking[0], bike_model=booking[1], service_type=booking[2], date=booking[3], shop_number=booking[4], status=booking[5], track_link=booking[6])
        return render_template('track.html', booking=booking, google_maps_link=GOOGLE_MAPS_LINK)
    flash('Booking not found!', 'error')
    return redirect(url_for('home'))

@app.route('/services')
def services():
    services = [
        {"name": "Oil Change", "description": "Complete oil change with premium oil.", "price": "50 rups", "duration": "1 hour", "image": "oil.jpg"},
        {"name": "EFI Tuning and Diagnostics", "description": "Your EFI system is responsible for delivering the fuel into your engine and it can possibly be tuned to alter.", "price": "rups", "duration": "2 hours", "image": "ecu.jpg"},
        {"name": "Full Service", "description": "Comprehensive service including oil, brakes, and more.", "price": "500 rups", "duration": "6 hours", "image": "service.jpg"}
    ]
    return render_template('services.html', services=services)

@app.route('/review/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def review(booking_id):
    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO reviews (user_id, booking_id, rating, comment) VALUES (?, ?, ?, ?)",
                  (current_user.id, booking_id, rating, comment))
        conn.commit()
        conn.close()
        flash('Review submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('review.html', booking_id=booking_id)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE username = ?", (username,))
        admin = c.fetchone()
        conn.close()
        if admin and bcrypt.checkpw(password.encode('utf-8'), admin[2].encode('utf-8')):
            session['admin'] = True
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials!', 'error')
    return render_template('admin.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT b.id, b.user_id, b.bike_model, b.service_type, b.date, b.shop_number, b.status, u.username, b.track_link FROM bookings b JOIN users u ON b.user_id = u.id")
    bookings = c.fetchall()
    conn.close()
    bookings = [dict(id=row[0], user_id=row[1], bike_model=row[2], service_type=row[3], date=row[4], shop_number=row[5], status=row[6], username=row[7], track_link=row[8]) for row in bookings]
    return render_template('admin_dashboard.html', bookings=bookings)

@app.route('/admin/update_status/<int:booking_id>', methods=['POST'])
def update_status(booking_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    status = request.form['status']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
    conn.commit()

    # Fetch booking details for WhatsApp message
    c.execute("SELECT b.id, b.user_id, b.bike_model, b.service_type, b.date, b.shop_number, b.status, u.username, u.phone, b.track_link FROM bookings b JOIN users u ON b.user_id = u.id WHERE b.id = ?", (booking_id,))
    booking = c.fetchone()
    conn.close()

    if booking and booking[8]:
        pdf_file = generate_pdf(booking[0], booking[7], booking[2], booking[3], booking[4], booking[5], booking[9])
        send_whatsapp_message(booking[8], booking[0], booking[7], booking[2], booking[3], booking[4], booking[5], booking[6], pdf_file, booking[9])
    else:
        flash('User phone number not available for WhatsApp notification.', 'error')

    flash('Booking status updated!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_date/<int:booking_id>', methods=['POST'])
def update_date(booking_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    date = request.form['date']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE bookings SET date = ? WHERE id = ?", (date, booking_id))
    conn.commit()

    # Fetch booking details for WhatsApp message
    c.execute("SELECT b.id, b.user_id, b.bike_model, b.service_type, b.date, b.shop_number, b.status, u.username, u.phone, b.track_link FROM bookings b JOIN users u ON b.user_id = u.id WHERE b.id = ?", (booking_id,))
    booking = c.fetchone()
    conn.close()

    if booking and booking[8]:
        pdf_file = generate_pdf(booking[0], booking[7], booking[2], booking[3], booking[4], booking[5], booking[9])
        send_whatsapp_message(booking[8], booking[0], booking[7], booking[2], booking[3], booking[4], booking[5], booking[6], pdf_file, booking[9])
    else:
        flash('User phone number not available for WhatsApp notification.', 'error')

    flash('Booking date updated!', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
