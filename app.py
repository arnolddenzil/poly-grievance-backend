from flask import Flask, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_marshmallow import Marshmallow
from flask_cors import CORS
import datetime
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import configparser
from functools import wraps

# Need to add feature to delete a user and update user details such as password, email etc

parser = configparser.ConfigParser()
parser.read('config.ini')

db_username = parser.get('database', 'db_username')
db_password = parser.get('database', 'db_password')
db_host = parser.get('database', 'db_host')
db_name = parser.get('database', 'db_name')

student_start_index = int(parser.get('database', 'student_start_index'))
teacher_start_index = int(parser.get('database', 'teacher_start_index'))
admin_start_index = int(parser.get('database', 'admin_start_index'))


app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_username}:{db_password}@{db_host}/{db_name}"
app.config['SECRET_KEY'] = '8BYkEfBA6O6donWlSihBXox7C0sKR6bfi5'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)
#
#
class GrievanceBox(db.Model):
    __tablename__ = "grievance_box"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text(), nullable=False)
    created_on = db.Column(db.DATETIME, nullable=False, default=datetime.datetime.now())
    status = db.Column(db.Boolean, server_default='0', default=False, unique=False)
    status_updated = db.Column(db.DATETIME)
    actions = db.Column(db.Text())
    actions_updated = db.Column(db.DATETIME)
    comments = db.Column(db.Text())
    comments_updated = db.Column(db.DATETIME)
    student_id = db.Column(db.Integer, nullable=False)
    dept_code = db.Column(db.String(100))


# 1-100 -> Admins
# 101-300 -> Teachers
# 301 and above -> Students
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(100), nullable=False)


class Admin(UserMixin, db.Model):
    __tablename__ = "admin"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)


class Teacher(UserMixin, db.Model):
    __tablename__ = "teacher"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    dept_code = db.Column(db.String(100), nullable=False)


class Student(UserMixin, db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    sem = db.Column(db.Integer, nullable=False)
    dept_code = db.Column(db.String(100), nullable=False)


# Line below only required once, when creating DB.
db.create_all()

# The login manager contains the code that lets your application and Flask-Login work together,
# such as how to load a user from an ID, where to send users when they need to log in, and the like.
login_manager = LoginManager()

# Once the actual application object has been created, you can configure it for login with
login_manager.init_app(app)


# This callback is used to reload the user object from the user ID stored in the session.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class GrievanceBoxSchema(ma.Schema):
    class Meta:
        fields = ('id', 'title', 'body', 'date', 'status', 'status_updated', 'actions', 'actions_updated',
                  'comments', 'comments_updated', 'student_id', 'dept_code')


letter_schema = GrievanceBoxSchema()
letters_schema = GrievanceBoxSchema(many=True)


class StudentSchema(ma.Schema):
    class Meta:
        fields = ('id', 'email', 'password', 'name', 'sem', 'dept_code')


student_schema = StudentSchema()
students_schema = StudentSchema(many=True)


class TeacherSchema(ma.Schema):
    class Meta:
        fields = ('id', 'email', 'password', 'name', 'dept_code')


teacher_schema = TeacherSchema()
teachers_schema = TeacherSchema(many=True)


class AdminSchema(ma.Schema):
    class Meta:
        fields = ('id', 'email', 'password', 'name')


admin_schema = TeacherSchema()
admins_schema = TeacherSchema(many=True)


def require_role(role1, role2=""):
    """make sure user has this role"""
    def decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            print(f"Role1  :{role1} , Role2 :{role2}")
            print("User role : ", current_user.role)
            if not (current_user.role == role1 or current_user.role == role2):
                print("erangi poda")
                return {"error": "No access privilege"}

            else:
                print("u r authorized personal")
                return func(*args, **kwargs)
        return wrapped_function
    return decorator


@app.route('/user_details')
def user_details():
    print(current_user.id, current_user.role)
    user_id = current_user.id

    # if the current user is a student then their id in the User table will be above 300
    if user_id > student_start_index:
        search_id = user_id - student_start_index
        print("Id to search : ", search_id)
        student = Student.query.filter_by(id=search_id).first()
        return student_schema.jsonify(student)

    # if the current user is a teacher then their id in the User table will be above 100
    elif user_id > teacher_start_index:
        search_id = user_id - teacher_start_index
        print("Id to search : ", search_id)
        teacher = Teacher.query.filter_by(id=search_id).first()
        return teacher_schema.jsonify(teacher)

    # if the current user is an admin then their id in the User table will be above 0
    else:
        search_id = user_id - admin_start_index
        print("Id to search : ", search_id)
        admin = Admin.query.filter_by(id=search_id).first()
        return admin_schema.jsonify(admin)


@app.route('/student_login', methods=['POST'])
def student_login():
    email = request.json['email']
    password = request.json['password']

    student = Student.query.filter_by(email=email).first()

    if student is None:
        return {"error": "Email id not registered"}

    print(password)
    if not student.password == password:
        return {"error": "Incorrect Password"}

    user = User.query.filter_by(id=student_start_index+student.id).first()

    # Logs the user and creates a user session.....which means the user does not need to log in again each time to
    # access a protected page that only allows authorized user to access
    login_user(user)

    return {"response": "logged in"}


@app.route('/teacher_login', methods=['POST'])
def teacher_login():
    email = request.json['email']
    password = request.json['password']

    teacher = Teacher.query.filter_by(email=email).first()

    if teacher is None:
        return {"error": "Email id not registered"}

    if not teacher.password == password:
        return {"error": "Incorrect Password"}

    user = User.query.filter_by(id=teacher_start_index+teacher.id).first()

    # Logs the user and creates a user session.....which means the user does not need to log in again each time to
    # access a protected page that only allows authorized user to access
    login_user(user)

    return {"response": "logged in"}


@app.route('/admin_login', methods=['POST'])
def admin_login():
    email = request.json['email']
    password = request.json['password']

    admin = Admin.query.filter_by(email=email).first()

    if admin is None:
        return {"error": "Email id not registered"}

    if not admin.password == password:
        return {"error": "Incorrect Password"}

    user = User.query.filter_by(id=admin_start_index+admin.id).first()

    # Logs the user and creates a user session.....which means the user does not need to log in again each time to
    # access a protected page that only allows authorized user to access
    login_user(user)

    return {"response": "logged in"}


# Return all grievance letters -- Admin only
@app.route('/all_letters', methods=['GET'])
@login_required
@require_role(role1="Admin")
def get_all_letters():
    letters = GrievanceBox.query.all()
    result = letters_schema.dump(letters)
    return jsonify(result)


# Add a new letter --- Students only
@app.route('/add_letter', methods=['POST'])
@login_required
@require_role(role1="Student")
def add_letter():
    letter = GrievanceBox(
        title=request.json['title'],
        body=request.json['body'],
        student_id=request.json['student_id']
    )
    db.session.add(letter)
    db.session.commit()
    return letter_schema.jsonify(letter)


# Add a new student --- Admin only
@app.route('/add_student', methods=['POST'])
@login_required
@require_role(role1="Admin")
def add_student():
    name = request.json['name']
    email = request.json['email']
    password = request.json['password']
    sem = request.json['sem']
    dept_code = request.json['dept']

    student = Student.query.filter_by(email=email).first()
    if student:
        return {"error": "Student already exist"}

    student = Student(
        name=name,
        email=email,
        password=password,
        sem=sem,
        dept_code=dept_code
    )
    db.session.add(student)
    db.session.commit()

    # create a user in the user table for the new student
    new_user = User(id=student_start_index+student.id, role="Student")
    db.session.add(new_user)
    db.session.commit()

    print(student.name, student.id, student.email)
    return student_schema.jsonify(student)


# Return all students --- Admin only
@app.route('/all_students', methods=['GET'])
@login_required
@require_role(role1="Admin")
def get_all_students():
    students = Student.query.all()
    result = students_schema.dump(students)
    return jsonify(result)


# Add a new teacher --- Admin only
@app.route('/add_teacher', methods=['POST'])
@login_required
@require_role(role1="Admin")
def add_teacher():
    name = request.json['name']
    email = request.json['email']
    password = request.json['password']
    dept_code = request.json['dept']

    teacher = Teacher.query.filter_by(email=email).first()
    if teacher:
        return {"error": "Teacher already exist"}

    teacher = Teacher(
        name=name,
        email=email,
        password=password,
        dept_code=dept_code
    )
    db.session.add(teacher)
    db.session.commit()

    # create a user in the user table for the new student
    new_user = User(id=teacher_start_index + teacher.id, role="Teacher")
    db.session.add(new_user)
    db.session.commit()

    return teacher_schema.jsonify(teacher)


# Return all teachers --- Admin only
@app.route('/all_teachers', methods=['GET'])
@login_required
@require_role(role1="Admin")
def get_all_teachers():
    teachers = Teacher.query.all()
    result = students_schema.dump(teachers)
    return jsonify(result)


# Add a new admin --- Admin only
@app.route('/add_admin', methods=['POST'])
@login_required
@require_role(role1="Admin")
def add_admin():
    name = request.json['name']
    email = request.json['email']
    password = request.json['password']

    admin = Admin.query.filter_by(email=email).first()
    if admin:
        return {"error": "Admin already exist"}

    admin = Admin(
        name=name,
        email=email,
        password=password
    )
    db.session.add(admin)
    db.session.commit()

    # create a user in the user table for the new student
    new_user = User(id=admin_start_index+admin.id, role="Admin")
    db.session.add(new_user)
    db.session.commit()

    return teacher_schema.jsonify(admin)


# Return all admins --- Admin only
@app.route('/all_admins', methods=['GET'])
@login_required
@require_role(role1="Admin")
def get_all_admins():
    admins = Admin.query.all()
    result = students_schema.dump(admins)
    return jsonify(result)


# Get letter by id
@app.route("/get_letter/<int:letter_id>", methods=['GET'])
@login_required
def get_letter(letter_id):
    requested_letter = GrievanceBox.query.get(letter_id)
    return letter_schema.jsonify(requested_letter)


# Get letters registered by a logged in student in his dashboard
@app.route("/student_letters/<int:student_id>", methods=['GET'])
@login_required
def student_letters(student_id):
    letters = GrievanceBox.query.filter_by(student_id=student_id).all()
    result = letters_schema.dump(letters)
    return jsonify(result)


# Get letters registered to a department in the teacher dashboard -- Admin, Teachers
@app.route("/dept_letters/<string:dept_code>", methods=['GET'])
@login_required
@require_role(role1="Admin", role2="Teacher")
def dept_letters(dept_code):
    letters = GrievanceBox.query.filter_by(dept_code=dept_code).all()
    result = letters_schema.dump(letters)
    return jsonify(result)


# Get student details
@app.route("/student_details/<int:student_id>", methods=['GET'])
@login_required
def get_student(student_id):
    student = Student.query.get(student_id)
    return student_schema.jsonify(student)


# Get teacher details -- Admin, Teachers
@app.route("/teacher_details/<int:teacher_id>", methods=['GET'])
@login_required
@require_role(role1="Admin", role2="Teacher")
def get_teacher(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    return student_schema.jsonify(teacher)


# Get admin details -- Admin only
@app.route("/admin_details/<int:admin_id>", methods=['GET'])
@login_required
@require_role(role1="Admin")
def get_admin(admin_id):
    admin = Admin.query.get(admin_id)
    return student_schema.jsonify(admin)


# Update action, comment, status and dept together -- Admin only
@app.route("/action_comment_status_dept_update/<int:letter_id>", methods=['PUT'])
@login_required
@require_role(role1="Admin")
def action_comment_status_dept_update(letter_id):
    letter = GrievanceBox.query.get(letter_id)

    updated_action = request.json["actions"]
    updated_comment = request.json["comments"]
    updated_status = request.json["status"]
    updated_dept = request.json["dept"]

    if not letter.actions == updated_action:
        letter.actions = updated_action
        letter.actions_updated = datetime.datetime.now()

    if not letter.comments == updated_comment:
        letter.comments = updated_comment
        letter.comments_updated = datetime.datetime.now()

    if not letter.status == updated_status:
        letter.status = updated_status
        letter.status_updated = datetime.datetime.now()

    if not letter.dept_code == updated_dept:
        letter.dept_code = updated_dept

    db.session.commit()

    return letter_schema.jsonify(letter)


# Update Dept of letter -- Admin only
@app.route("/dept_update/<int:letter_id>", methods=['PUT'])
@login_required
@require_role(role1="Admin")
def dept_update(letter_id):
    letter = GrievanceBox.query.get(letter_id)

    updated_dept = request.json["dept"]

    if not letter.dept_code == updated_dept:
        letter.dept_code = updated_dept

    db.session.commit()

    return letter_schema.jsonify(letter)


# Update status -- Admin only
@app.route("/status_update/<int:letter_id>", methods=['PUT'])
@login_required
@require_role(role1="Admin")
def status_update(letter_id):
    letter = GrievanceBox.query.get(letter_id)

    updated_status = request.json["status"]

    if not letter.status == updated_status:
        letter.status = updated_status
        letter.status_updated = datetime.datetime.now()

    db.session.commit()

    return letter_schema.jsonify(letter)


# Update action -- Admin only
@app.route("/action_update/<int:letter_id>", methods=['PUT'])
@login_required
@require_role(role1="Admin")
def action_update(letter_id):
    letter = GrievanceBox.query.get(letter_id)

    updated_action = request.json["actions"]

    if not letter.actions == updated_action:
        letter.actions = updated_action
        letter.actions_updated = datetime.datetime.now()

    db.session.commit()

    return letter_schema.jsonify(letter)


# Update comment -- Admin , Teachers
@app.route("/comment_update/<int:letter_id>", methods=['PUT'])
@login_required
@require_role(role1="Admin", role2="Teacher")
def comment_update(letter_id):
    letter = GrievanceBox.query.get(letter_id)

    updated_comment = request.json["comments"]

    if not letter.comments == updated_comment:
        letter.comments = updated_comment
        letter.comments_updated = datetime.datetime.now()

    db.session.commit()

    return letter_schema.jsonify(letter)


# Delete a letter -- Admin , Students
@app.route("/delete_letter/<int:letter_id>", methods=['DELETE'])
@login_required
@require_role(role1="Admin", role2="Student")
def delete_letter(letter_id):
    letter_to_delete = GrievanceBox.query.get(letter_id)
    db.session.delete(letter_to_delete)
    db.session.commit()
    letters = GrievanceBox.query.all()
    result = letters_schema.dump(letters)
    return jsonify(result)



# The logout also requires '@login_required' to check whether the user is logged in as it makes no sense to logout otherwise
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return {"response": "logged out"}


if __name__ == "__main__":
    app.run(debug=True)

