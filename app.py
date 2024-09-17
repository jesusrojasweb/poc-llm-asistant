import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from models import db, ChatMessage
from chatbot import initialize_conversation, get_chatbot_response, reset_conversation

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

db.init_app(app)

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp).all()
    initial_history = [{'role': 'user' if msg.is_user else 'assistant', 'content': msg.content} for msg in messages]
    initialize_conversation(initial_history)
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    
    # Save user message to database
    chat_message = ChatMessage(content=user_message, is_user=True)
    db.session.add(chat_message)
    db.session.commit()
    
    # Get chatbot response
    bot_response = get_chatbot_response(user_message)
    
    # Save bot response to database
    bot_message = ChatMessage(content=bot_response, is_user=False)
    db.session.add(bot_message)
    db.session.commit()
    
    return jsonify({'response': bot_response})

@app.route('/reset_conversation', methods=['POST'])
def reset_chat():
    reset_conversation()
    ChatMessage.query.delete()
    db.session.commit()
    return jsonify({'message': 'Conversation reset successfully'})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        file_url = f"/uploads/{filename}"
        
        # Save file message to database
        file_message = ChatMessage(content=f"File uploaded: {file_url}", is_user=True)
        db.session.add(file_message)
        db.session.commit()
        
        return jsonify({'message': 'File uploaded successfully', 'file_url': file_url})
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/history')
def get_chat_history():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp).all()
    history = [{'content': msg.content, 'is_user': msg.is_user} for msg in messages]
    return jsonify(history)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
