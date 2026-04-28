# Code updated and bug fixed by GoogleAI (provided references for building) & ChatGPT (bug fixed + example code)
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

data_dir = os.path.join(basedir, 'Data')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///' + os.path.join(data_dir, 'users.db')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "ChangeMeToSomethingSecret"

db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AccType = db.Column(db.String(12))
    name = db.Column(db.String(50), unique=True, nullable=False)
    pw = db.Column(db.String, nullable=False)

with app.app_context():
    db.create_all()

    user = User.query.filter_by(name="Tester1").first()
    if not user:
        user = User(id = "001", AccType="Administrator", name="Tester1", pw="Password")
        db.session.add(user)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)