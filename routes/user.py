# routes/user.py

from flask import Blueprint, request, jsonify, session
from flask_bcrypt import Bcrypt
from Helpers.ServiceApp import db, generate_token, verify_token
from Models.UserModel import User

bcrypt = Bcrypt()

# Create Blueprint for add_user route
add_user = Blueprint('add_user', __name__)

@add_user.route('/api/add_user', methods=['POST'])
def add_user_route():
    data = request.get_json()
    username = data['username']
    email = data['email'] 
    password = data['password']

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"message": "Email already exists. Please use a different email."}), 400

    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User added successfully!"}), 201


# Create Blueprint for get_users route
get_users = Blueprint('get_users', __name__)

@get_users.route('/api/get_users', methods=['GET'])
def get_users_route():
    token = None
    print("TEST1")
    if 'Authorization' in request.headers:
        token = request.headers['Authorization'].split(" ")[1]
        if not verify_token(token):
            print("TEST2")
            return jsonify({"message": "Access denied, token is invalid"}), 401
    else:
        print("TEST3")
        return jsonify({'message': 'Token is missing'}), 401
    
    if token:
        print("TEST4")
        payload = verify_token(token)
        if payload:
            print("TEST5")
            request_user_id = str(request.json["CookiesId"])
            
            users = User.query.all
            print("TEST")
            print(users)
            return jsonify([user.to_dict() for user in users]), 200
    else:
        return jsonify({"message": "Access denied"}), 401

# Create Blueprint for login route
login = Blueprint('login', __name__)

@login.route('/api/login', methods=['POST'])
def login_route():
    data = request.get_json()
    email = data['email']
    password = data['password']
    
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        # generate token
        token = generate_token(user)
        user_id = user.id
        session['user_id'] = user_id
        return jsonify({"message": "Login successful","user": user.to_dict(), "token": token}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401