from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##CONNECT TO GRAVATAR
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONFIGURE TABLES
# THIS IS THE CHILD
class BlogPost(db.Model, Base):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # ESTABLISH 2-WAY RELATIONSHIP WITH OTHER SCHEMA 'USER'
    # the author property of BlogPost is now a User object
    author = relationship('User', back_populates='posts')

    # # user.id refers to the id column of the table 'user'

    author_id= db.Column(db.Integer, db.ForeignKey('user.id'))


    # blogpost can have many comments
    comments= relationship("Comments", back_populates='owning_post')


    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


# THIS IS THE PARENTS
class User(db.Model, UserMixin, Base):
    __tablename__= 'user'
    id = db.Column(db.Integer, primary_key=True)
    email= db.Column(db.String(250),nullable= False)
    name= db.Column(db.String(250),nullable= False)
    password= db.Column(db.String(250), nullable=False)

    # ESTABLISH RELATIONSHIP WITH OTHER SCHEMA 'BlogPost'--> 'POSTS' IS A LIST OF POSTS CREATED BY A CERTAIN USER
    # The "author" refers to the author property in the BlogPost class.
    posts= relationship('BlogPost',back_populates="author")

    comments= relationship("Comments", back_populates='author')



class Comments(db.Model, UserMixin, Base):
    __tablename__='comments'

    author= relationship('User', back_populates='comments')
    owning_post= relationship('BlogPost', back_populates='comments')

    author_id= db.Column(db.Integer, db.ForeignKey('user.id'))
    owning_post_id= db.Column(db.Integer, db.ForeignKey('blog_posts.id'))

    id = db.Column(db.Integer, primary_key=True)
    text= db.Column(db.String(500), nullable=False)


db.create_all()
def admin_ony(function):
    def wrapper(*args, **kwargs):
        if current_user.is_anonymous:
            return abort (403)
        elif current_user.id!=1:
            return abort (403)
        else:
            return function(*args, **kwargs)

    wrapper.__name__ = function.__name__
    return wrapper


##CONNECT TO FLASK_LOGIN
login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)

@app.route('/register', methods=["POST","GET"])
def register():
    form= RegisterForm()
    if form.validate_on_submit():
        new_user= User()
        new_user.password = generate_password_hash(password=form.password.data, method='pbkdf2:sha256', salt_length=8)
        new_user.name = form.name.data
        new_user.email = form.email.data
        # if User.query.all()==[]:
        #     new_user.id=0
        # else:
        #     new_user.id= int(User.query.all()[-1].id)+1

        for user in User.query.all():
            if user.name== form.name.data:
                flash(message='You have entered existing username. Try again.')
                if user.email == form.email.data:
                    flash(message='You have entered existing email. Trying to log in?')
                return redirect('/register')
            if user.email== form.email.data:
                flash(message='You have entered existing email. Trying to log in?')

                return redirect('/register')


        db.session.add(new_user)
        db.session.commit()

        # log the newly registered user in
        login_user(new_user)

        return redirect('/')
    return render_template("register.html", form= form)


@app.route('/login', methods= ['POST', "GET"])
def login():
    form= LoginForm()
    if form.validate_on_submit():
        typed_email= form.email.data
        typed_password= form.password.data

        user= User.query.filter_by(email= typed_email).first()
        if not user:
            flash(message='User can not be found. Try again. Trying to register?')
            return redirect('/login')

        else:
            if check_password_hash(pwhash=user.password,password=typed_password):
                login_user(user)
                return redirect('/')
            else:
                flash(message='Password is wrong. Try again')
                return redirect('/login')


    return render_template("login.html", form= form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['POST',"GET"])
def show_post(post_id):
    form= CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment= Comments(
                text= form.comment.data,
                owning_post_id= post_id,
                author_id= current_user.id
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))
        else:
            flash(message="Please login.")
            return redirect(url_for('show_post', post_id= post_id))

    requested_post = BlogPost.query.get(post_id)
    return render_template("post.html", post=requested_post, form= form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods= ['POST','GET'])
@admin_ony
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["POST",'GET'])
@admin_ony
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author.name,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author.name = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)



@app.route("/delete/<int:post_id>")
@admin_ony
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
