"""
Sakkara Stats - Blood Sugar Monitoring System
Developed by Siddharth - 2025
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, login_required, 
                        logout_user, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sakkara-stats-siddharth-2025-secure-key')

# Database configuration for Render deployment
if os.environ.get('DATABASE_URL'):
    # Production database (Render PostgreSQL)
    database_url = os.environ.get('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local development database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sakkara_stats.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    before_food_min = db.Column(db.Integer, default=80)
    before_food_max = db.Column(db.Integer, default=130)
    after_food_min = db.Column(db.Integer, default=90)
    after_food_max = db.Column(db.Integer, default=180)
    readings = db.relationship('Reading', backref='user', lazy=True)

class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_of_day = db.Column(db.String(20), nullable=False)
    meal_relation = db.Column(db.String(20), nullable=False)
    sugar_value = db.Column(db.Integer, nullable=False)
    food_eaten = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_active:
                login_user(user)
                if user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Your account is deactivated. Please contact admin.', 'error')
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
        else:
            user = User(
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    # Get user's readings
    readings = Reading.query.filter_by(user_id=current_user.id).order_by(
        Reading.date.desc(), Reading.created_at.desc()).limit(10).all()
    
    # Calculate stats
    all_readings = Reading.query.filter_by(user_id=current_user.id).all()
    if all_readings:
        total_readings = len(all_readings)
        avg_sugar = sum(r.sugar_value for r in all_readings) / total_readings
        min_sugar = min(r.sugar_value for r in all_readings)
        max_sugar = max(r.sugar_value for r in all_readings)
        
        before_food_readings = [r for r in all_readings 
                               if r.meal_relation == 'Before Food']
        after_food_readings = [r for r in all_readings 
                              if r.meal_relation == 'After Food']
        
        before_avg = (sum(r.sugar_value for r in before_food_readings) / 
                     len(before_food_readings) if before_food_readings else 0)
        after_avg = (sum(r.sugar_value for r in after_food_readings) / 
                    len(after_food_readings) if after_food_readings else 0)
    else:
        total_readings = avg_sugar = min_sugar = max_sugar = 0
        before_avg = after_avg = 0
    
    stats = {
        'total_readings': total_readings,
        'avg_sugar': round(avg_sugar, 1),
        'min_sugar': min_sugar,
        'max_sugar': max_sugar,
        'before_avg': round(before_avg, 1),
        'after_avg': round(after_avg, 1)
    }
    
    return render_template('dashboard.html', readings=readings, stats=stats)

@app.route('/add_reading', methods=['POST'])
@login_required
def add_reading():
    reading = Reading(
        user_id=current_user.id,
        date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
        time_of_day=request.form['time_of_day'],
        meal_relation=request.form['meal_relation'],
        sugar_value=int(request.form['sugar_value']),
        food_eaten=request.form['food_eaten']
    )
    db.session.add(reading)
    db.session.commit()
    flash('Reading added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/history')
@login_required
def history():
    if current_user.role == 'admin':
        return redirect(url_for('manage_readings'))
    
    readings = Reading.query.filter_by(user_id=current_user.id).order_by(
        Reading.date.desc(), Reading.created_at.desc()).all()
    return render_template('history.html', readings=readings)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        # Update name if provided
        if 'name' in request.form and request.form['name'].strip():
            current_user.name = request.form['name'].strip()
        
        # Update blood sugar ranges
        current_user.before_food_min = int(request.form['before_food_min'])
        current_user.before_food_max = int(request.form['before_food_max'])
        current_user.after_food_min = int(request.form['after_food_min'])
        current_user.after_food_max = int(request.form['after_food_max'])
        
        # Update password if provided
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if new_password:  # Only if new password is provided
            if new_password == confirm_password:
                current_user.password_hash = generate_password_hash(new_password)
                flash('Profile and password updated successfully!', 'success')
            else:
                flash('Passwords do not match!', 'error')
                return redirect(url_for('profile'))
        else:
            flash('Profile updated successfully!', 'success')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'error')
    
    return redirect(url_for('profile'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    total_users = User.query.count()
    total_readings = Reading.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    
    # Calculate average sugar across all users
    all_readings = Reading.query.all()
    avg_sugar = (sum(r.sugar_value for r in all_readings) / 
                len(all_readings) if all_readings else 0)
    
    before_food_readings = [r for r in all_readings 
                           if r.meal_relation == 'Before Food']
    after_food_readings = [r for r in all_readings 
                          if r.meal_relation == 'After Food']
    
    before_avg = (sum(r.sugar_value for r in before_food_readings) / 
                 len(before_food_readings) if before_food_readings else 0)
    after_avg = (sum(r.sugar_value for r in after_food_readings) / 
                len(after_food_readings) if after_food_readings else 0)
    
    stats = {
        'total_users': total_users,
        'total_readings': total_readings,
        'active_users': active_users,
        'avg_sugar': round(avg_sugar, 1),
        'before_avg': round(before_avg, 1),
        'after_avg': round(after_avg, 1)
    }
    
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/manage_users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/manage_readings')
@login_required
def manage_readings():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    readings = Reading.query.join(User).order_by(
        Reading.date.desc(), Reading.created_at.desc()).all()
    return render_template('manage_readings.html', readings=readings)

@app.route('/toggle_user/<int:user_id>')
@login_required
def toggle_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status = "activated" if user.is_active else "deactivated"
    flash(f'User {user.email} has been {status}.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/reset_user_password/<int:user_id>')
@login_required
def reset_user_password(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    # Set a temporary password
    temp_password = "TempPass123!"
    user.password_hash = generate_password_hash(temp_password)
    db.session.commit()
    
    flash(f'Password reset for {user.email}. Temporary password: {temp_password}', 'success')
    return redirect(url_for('manage_users'))

@app.route('/delete_reading/<int:reading_id>')
@login_required
def delete_reading(reading_id):
    reading = Reading.query.get_or_404(reading_id)
    
    # Users can only delete their own readings, admins can delete any
    if current_user.role != 'admin' and reading.user_id != current_user.id:
        flash('Unauthorized action.', 'error')
        return redirect(url_for('history'))
    
    db.session.delete(reading)
    db.session.commit()
    flash('Reading deleted successfully!', 'success')
    
    if current_user.role == 'admin':
        return redirect(url_for('manage_readings'))
    else:
        return redirect(url_for('history'))

@app.route('/api/chart_data')
@login_required
def chart_data():
    if current_user.role == 'admin':
        # Admin sees all data
        readings = Reading.query.join(User).order_by(Reading.date.asc()).all()
    else:
        # Users see only their data
        readings = Reading.query.filter_by(user_id=current_user.id).order_by(
            Reading.date.asc()).all()
    
    before_food_data = []
    after_food_data = []
    
    for reading in readings:
        data_point = {
            'x': reading.date.strftime('%Y-%m-%d'),
            'y': reading.sugar_value,
            'food': reading.food_eaten,
            'time': reading.time_of_day,
            'user_email': (reading.user.email 
                          if current_user.role == 'admin' else None)
        }
        
        if reading.meal_relation == 'Before Food':
            before_food_data.append(data_point)
        else:
            after_food_data.append(data_point)
    
    return jsonify({
        'before_food': before_food_data,
        'after_food': after_food_data,
        'before_food_range': {
            'min': current_user.before_food_min,
            'max': current_user.before_food_max
        },
        'after_food_range': {
            'min': current_user.after_food_min,
            'max': current_user.after_food_max
        }
    })

def create_admin_user():
    """Create admin user if it doesn't exist"""
    admin_email = "siddhuplr@gmail.com"
    admin_password = "Sakkara@2025"
    
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {admin_email}")

@app.route('/test_chart')
def test_chart():
    """Test route to check if Chart.js is working"""
    return render_template('test_chart.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_user()
    
    # Production configuration
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
    