import matplotlib.pyplot as plt  # For generating workout progress charts
import io  # For handling byte streams in memory
import base64  # For encoding images to display in HTML
import pandas as pd  # For exporting workouts as CSV
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response  # Ensure Response is imported
from flask_sqlalchemy import SQLAlchemy  # Database management
from flask_mail import Mail, Message  # For sending email reminders
from werkzeug.security import generate_password_hash, check_password_hash  # Secure password hashing
from datetime import datetime, timedelta  # Handling dates and time calculations


app = Flask(__name__)

# Secret key for session management
app.secret_key = "supersecretkey"

# Database configuration (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///workout.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)


# Workout model
class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    exercise = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes

# Create database tables within app context
with app.app_context():
    db.create_all()

# Home Route (Register & Login Page)
@app.route('/')
def home():
    return render_template('register_login.html')

# Register Route
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    if not username or not email or not password:
        flash("All fields are required!", "danger")
        return redirect(url_for('home'))

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash("Email already registered! Please log in.", "warning")
        return redirect(url_for('home'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, email=email, password=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    flash("Registration successful! Please log in.", "success")
    return redirect(url_for('home'))

# Login Route
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['username'] = user.username
        flash(f"Welcome, {user.username}!", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Invalid email or password. Try again.", "danger")
        return redirect(url_for('home'))

# Dashboard Route (Protected)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))

    return render_template('dashboard.html', username=session['username'])

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('home'))


# Track Workouts Route
@app.route('/track_workouts', methods=['GET', 'POST'])
def track_workouts():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        date_str = request.form.get('date')
        exercise = request.form.get('exercise')
        duration = request.form.get('duration')

        if not date_str or not exercise or not duration:
            flash("All fields are required!", "danger")
            return redirect(url_for('track_workouts'))

        # Convert date string to Python date object
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        new_workout = Workout(user_id=session['user_id'], date=date_obj, exercise=exercise, duration=int(duration))
        db.session.add(new_workout)
        db.session.commit()

        flash("Workout added successfully!", "success")
        return redirect(url_for('view_workouts'))

    return render_template('track_workouts.html')


# View Workouts Route
@app.route('/workouts')
def view_workouts():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))
    


    workouts = Workout.query.filter_by(user_id=session['user_id']).all()
    return render_template('view_workouts.html', workouts=workouts)

# Add Workout Route
@app.route('/add_workout', methods=['GET', 'POST'])
def add_workout():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        date = request.form.get('date')
        exercise = request.form.get('exercise')
        duration = request.form.get('duration')

        if not date or not exercise or not duration:
            flash("All fields are required!", "danger")
            return redirect(url_for('add_workout'))


        new_workout = Workout(user_id=session['user_id'], date=date, exercise=exercise, duration=duration)
        db.session.add(new_workout)
        db.session.commit()

        flash("Workout added successfully!", "success")
        return redirect(url_for('view_workouts'))

    return render_template('add_workout.html')

# Edit Workout Route
@app.route('/edit_workout/<int:id>', methods=['GET', 'POST'])
def edit_workout(id):
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))

    workout = Workout.query.get_or_404(id)

    if request.method == 'POST':
        workout.date = request.form.get('date')
        workout.exercise = request.form.get('exercise')
        workout.duration = request.form.get('duration')

        db.session.commit()
        flash("Workout updated successfully!", "success")
        return redirect(url_for('view_workouts'))

    return render_template('edit_workout.html', workout=workout)

# Delete Workout Route
@app.route('/delete_workout/<int:id>', methods=['POST'])
def delete_workout(id):
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))

    workout = Workout.query.get_or_404(id)
    db.session.delete(workout)
    db.session.commit()

    flash("Workout deleted successfully!", "success")
    return redirect(url_for('view_workouts'))

@app.route('/achievements')
def achievements():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user = User.query.get(session['user_id'])
    workouts = Workout.query.filter_by(user_id=user.id).all()

    # Dictionary to store count of workouts for each exercise
    exercise_achievements = {}

    for workout in workouts:
        exercise = workout.exercise
        if exercise not in exercise_achievements:
            exercise_achievements[exercise] = 1
        else:
            exercise_achievements[exercise] += 1

    # Dictionary to store badges earned per exercise
    badges = {}

    for exercise, count in exercise_achievements.items():
        badges[exercise] = []  # Initialize badge list for each exercise
        if count >= 5:
            badges[exercise].append("🏅 Beginner: Completed 5 " + exercise + " workouts")
        if count >= 10:
            badges[exercise].append("🥈 Intermediate: Completed 10 " + exercise + " workouts")
        if count >= 20:
            badges[exercise].append("🥇 Pro: Completed 20 " + exercise + " workouts")

    return render_template('achievements.html', badges=badges)

# 📅 Workout Calendar Feature
@app.route('/calendar')
def workout_calendar():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    workouts = Workout.query.filter_by(user_id=session['user_id']).all()
    return render_template('calendar.html', workouts=workouts)

# 📊 Workout Statistics Feature
@app.route('/statistics')
def statistics():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    workouts = Workout.query.filter_by(user_id=session['user_id']).all()
    dates = [workout.date.strftime('%Y-%m-%d') for workout in workouts]
    durations = [workout.duration for workout in workouts]

    plt.figure(figsize=(8, 4))
    plt.plot(dates, durations, marker='o', linestyle='-', color='blue')
    plt.xlabel('Date')
    plt.ylabel('Duration (minutes)')
    plt.title('Workout Progress')
    plt.xticks(rotation=45)
    plt.grid()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode()

    return render_template('statistics.html', img_base64=img_base64)

# 🔔 Workout Reminder via Email Feature
@app.route('/set_reminder', methods=['POST'])
def set_reminder():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user = User.query.get(session['user_id'])
    msg = Message("Workout Reminder", sender="your-email@gmail.com", recipients=[user.email])
    msg.body = "Hey! Don't forget to log your workout today!"
    mail.send(msg)

    flash("Reminder email sent!", "success")
    return redirect(url_for('dashboard'))

# 📥 Export Workouts as CSV Feature
@app.route('/export_workouts')
def export_workouts():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    workouts = Workout.query.filter_by(user_id=session['user_id']).all()
    data = [{"Date": w.date, "Exercise": w.exercise, "Duration": w.duration} for w in workouts]
    df = pd.DataFrame(data)
    csv_data = df.to_csv(index=False)

    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=workouts.csv"})

# 📈 Workout Streak Tracker Feature
@app.route('/streak')
def workout_streak():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    workouts = Workout.query.filter_by(user_id=session['user_id']).order_by(Workout.date).all()

    if not workouts:
        flash("No workouts found. Start tracking your workouts!", "info")
        return redirect(url_for('dashboard'))

    streak = 0
    max_streak = 0
    prev_date = None

    for workout in workouts:
        if prev_date and (workout.date - prev_date).days == 1:
            streak += 1
        else:
            streak = 1  # Reset streak if a day is skipped

        max_streak = max(max_streak, streak)
        prev_date = workout.date

    return render_template('streak.html', max_streak=max_streak, streak=streak)


# View Progress Route
@app.route('/view_progress')
def view_progress():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))

    try:
        # Fetch all workouts for the logged-in user
        workouts = Workout.query.filter_by(user_id=session['user_id']).all()

        # Calculate progress (e.g., total duration of workouts, number of workouts, etc.)
        total_duration = sum(workout.duration for workout in workouts)
        total_workouts = len(workouts)
    except:
        workouts = []
        total_duration = 0
        total_workouts = 0

    # Pass the progress data and workouts to the template
    return render_template('view_progress.html', total_duration=total_duration, total_workouts=total_workouts, workouts=workouts)

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)
