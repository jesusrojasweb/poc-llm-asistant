import os
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, ChatMessage, User
from chatbot import initialize_conversation, get_chatbot_response, reset_conversation, upload_pdf, get_vector_store_id
from datetime import timedelta, datetime
from flask_socketio import SocketIO, emit
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'qLiAAc92kN98OojsXFoSUvSQZuSw9Jiq')
print(f"SECRET_KEY: {app.config['SECRET_KEY']}")

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=14)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=14)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'my_session_cookie'

db.init_app(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = None
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=14)

@app.route('/')
@login_required
def index():
    print(f"Accessing index route. User authenticated: {current_user.is_authenticated}")
    print(f"Current user: {current_user}")
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    initial_history = [{
        'role': 'user' if msg.is_user else 'assistant',
        'content': msg.content
    } for msg in messages]
    initialize_conversation(initial_history)
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']

            print(f"Attempting to register user: {username}")

            user = User.query.filter_by(username=username).first()
            if user:
                print(f"Username {username} already exists")
                flash('Username already exists. Please choose a different username.', 'error')
                return redirect(url_for('register'))

            email_user = User.query.filter_by(email=email).first()
            if email_user:
                print(f"Email {email} already registered")
                flash('Email already registered. Please use a different email address.', 'error')
                return redirect(url_for('register'))

            new_user = User(username=username, email=email, password_hash=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()

            print(f"User {username} registered successfully")
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error during registration: {str(e)}")
            app.logger.error(f"Error during registration: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        print(f"User {current_user.username} is already authenticated, redirecting to index")
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        print(f"Attempting to log in user: {username}")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            session['logged_in'] = True
            session.modified = True
            print(f"User {username} logged in successfully")
            print(f"current_user.is_authenticated: {current_user.is_authenticated}")
            print(f"current_user: {current_user}")
            print(f"session: {session}")
            app.logger.info(f"User {username} logged in successfully")
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            print(f"Next page: {next_page}")
            return redirect(next_page or url_for('index'))
        else:
            print(f"Failed login attempt for username: {username}")
            app.logger.warning(f"Failed login attempt for username: {username}")
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@socketio.on('send_message')
def handle_message(data):
    user_message = data['message']

    chat_message = ChatMessage(content=user_message, is_user=True, user_id=current_user.id)
    db.session.add(chat_message)
    db.session.commit()

    bot_response = get_chatbot_response(user_message)

    bot_message = ChatMessage(content=bot_response, is_user=False, user_id=current_user.id)
    db.session.add(bot_message)
    db.session.commit()

    emit('receive_message', {'message': bot_response, 'is_user': False, 'message_id': bot_message.id})

@socketio.on('reset_conversation')
def handle_reset():
    reset_conversation()
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    emit('conversation_reset')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        file_url = f"/uploads/{filename}"

        if filename.lower().endswith('.pdf'):
            file.stream.seek(0)
            vector_store_id = get_vector_store_id()
            upload_pdf(file_url, vector_store_id)

        file_message = ChatMessage(content=f"File uploaded: {file_url}", is_user=True, user_id=current_user.id)
        db.session.add(file_message)
        db.session.commit()

        return jsonify({'message': 'File uploaded successfully', 'file_url': file_url})

    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/history')
@login_required
def get_chat_history():
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    print(f"messages: {messages}")
    history = [{
        'content': msg.content,
        'is_user': msg.is_user,
        'feedback': msg.feedback,
        'thereIsFeedback': msg.there_is_feedback,
        'message_id': msg.id,
    } for msg in messages]
    return jsonify(history)

@app.route('/debug_users')
def debug_users():
    users = User.query.all()
    user_list = [{'id': user.id, 'username': user.username, 'email': user.email} for user in users]
    return jsonify(user_list)

@app.route('/debug_auth')
def debug_auth():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username, 'user_id': current_user.id})
    else:
        return jsonify({'authenticated': False})

@app.route('/check_session')
def check_session():
    return jsonify({
        'is_authenticated': current_user.is_authenticated,
        'user': str(current_user) if current_user.is_authenticated else None,
        'session': dict(session)
    })

@app.errorhandler(401)
def unauthorized(error):
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('login', next=request.url))

@app.route('/feedback', methods=['POST'])
@login_required
def handle_feedback():
    data = request.json
    message_id = data.get('message_id')
    is_like = data.get('is_like')

    print(f"Received feedback for message ID {message_id}: {is_like}")

    numeric_id = int(message_id)

    message = ChatMessage.query.filter_by(id=numeric_id, user_id=current_user.id).first()
    if message:
        message.feedback = is_like
        message.there_is_feedback = True
        db.session.commit()
        print(f"Feedback saved: Message ID: {numeric_id}, Like: {is_like}")
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Message not found"}), 404

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    return render_template('admin.html')

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    per_page = 10

    user_query = User.query
    if search:
        user_query = user_query.filter(User.username.ilike(f'%{search}%') | User.email.ilike(f'%{search}%'))

    pagination = user_query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items

    total_users = User.query.count()
    total_messages = ChatMessage.query.filter_by(is_user=True).count()
    avg_messages_per_user = db.session.query(func.avg(db.session.query(func.count(ChatMessage.id)).filter(ChatMessage.user_id == User.id).scalar_subquery())).scalar() or 0

    user_activity = get_user_activity()
    message_distribution = get_message_distribution()

    return jsonify({
        'users': [{'id': user.id, 'username': user.username} for user in users],
        'total_pages': pagination.pages,
        'statistics': {
            'total_users': total_users,
            'total_messages': total_messages,
            'avg_messages_per_user': float(avg_messages_per_user)
        },
        'chart_data': {
            'user_activity': user_activity,
            'message_distribution': message_distribution
        }
    })

def get_user_activity():
    last_week = datetime.utcnow() - timedelta(days=7)
    activity = db.session.query(
        func.date(ChatMessage.timestamp).label('date'),
        func.count(ChatMessage.id).label('count')
    ).filter(ChatMessage.timestamp >= last_week).group_by(func.date(ChatMessage.timestamp)).all()

    return {
        'labels': [str(day.date) for day in activity],
        'values': [day.count for day in activity]
    }

def get_message_distribution():
    user_messages = ChatMessage.query.filter_by(is_user=True).count()
    bot_messages = ChatMessage.query.filter_by(is_user=False).count()
    likes = ChatMessage.query.filter_by(feedback=True, there_is_feedback=True).count()
    dislikes = ChatMessage.query.filter_by(feedback=False, there_is_feedback=True).count()
    return {
        'user_messages': user_messages,
        'bot_messages': bot_messages,
        'likes': likes,
        'dislikes': dislikes
    }

@app.route('/admin/user_chat_history/<int:user_id>')
@login_required
def admin_user_chat_history(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.query.get_or_404(user_id)
    chat_messages = ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.timestamp).all()

    total_messages = len(chat_messages)

    # Solo cuenta likes y dislikes si there_is_feedback es True
    likes_count = sum(1 for msg in chat_messages if msg.feedback == True and msg.there_is_feedback == True)
    dislikes_count = sum(1 for msg in chat_messages if msg.feedback == False and msg.there_is_feedback == True)

    return jsonify({
        'chat_history': [
            {
                'content': message.content,
                'is_user': message.is_user,
                'timestamp': message.timestamp.isoformat(),
                # Solo muestra feedback si there_is_feedback es True, de lo contrario None
                'feedback': message.feedback if message.there_is_feedback else None
            } for message in chat_messages
        ],
        'stats': {
            'total_messages': total_messages,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count
        }
    })

def create_admin_user():
    with app.app_context():
        admin_user = User.query.filter_by(is_admin=True).first()
        if not admin_user:
            admin_user = User(username='admin', email='admin@example.com', password_hash=generate_password_hash('admin_password'), is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_user()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)