from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, validators, ValidationError, EmailField
from wtforms.validators import EqualTo, Email

class SignUpForm(FlaskForm):
    
    def validate_username(self, username):
        from app import get_db  
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username.data,))
        user = cursor.fetchone()
        if user:
            raise ValidationError("Username already exists. Please choose a different one.")
    
    def validate_email_address(self, email_address):
        from app import get_db  
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email_address = ?", (email_address.data,))
        user = cursor.fetchone()
        if user:
            raise ValidationError("Email address already registered. Please use a different one or Log In.")

    username = StringField(label = 'Username', validators=[validators.DataRequired(), validators.Length(min=2, max=25)])
    email_address = EmailField(label = 'Email Address', validators=[validators.DataRequired(), validators.Email()])
    password1 = PasswordField(label = 'Password', validators=[validators.DataRequired(), validators.Length(min=6, max=100)])
    password2 = PasswordField(label = 'Confirm Password', validators=[validators.DataRequired(), EqualTo('password1')])    
    submit = SubmitField(label = 'Sign Up')
    
class LoginForm(FlaskForm):
    username = StringField(label = 'Username', validators=[validators.DataRequired()])
    password = PasswordField(label = 'Password', validators=[validators.DataRequired()])
    submit = SubmitField(label = 'Log In')  
