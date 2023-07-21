import datetime
import requests
from flask import Flask, request, redirect, abort, jsonify
from flask import render_template, make_response, session
from flask_login import LoginManager, login_user, login_required
from flask_login import logout_user, current_user
from data import db_session
from data.news import News
from data.users import User
from forms.add_news import NewsForm
from forms.user import RegisterForm
from loginform import LoginForm


app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)

app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/news.sqlite'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)  # год


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

# ошибка 404
@app.errorhandler(404)
def http_404_error(error):
    return make_response(jsonify({'error': f'Новости не найдены!'}), 404)


@app.errorhandler(400)
def bad_request(_):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


@app.route('/error404')
def well():  # колодец
    return render_template('well.html')


@app.errorhandler(401)
def http_401_handler(error):
    return redirect('/login')


@app.route('/')
@app.route('/index')
def index():
    # работу с БД начинаем с открытия сессии
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        news = db_sess.query(News).filter(
            (News.user == current_user) | (News.is_private != True))
    else:
        news = db_sess.query(News).filter(News.is_private != True)
    return render_template('index.html',
                           title='Новости',
                           news=news)


@app.route('/news_del/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.id == id, News.user == current_user).first()
    if news:
        db_sess.delete(news)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/news', methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = News()  # ORM-модель News
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        current_user.news.append(news)
        db_sess.merge(current_user)  # слияние сессии с текущим пользователем
        db_sess.commit()
        return redirect('/')
    return render_template('news.html', title='Добавление новости',
                           form=form)


@app.route('/news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == 'GET':
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id, News.user == current_user).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('news.html', title='Редактирование новости',
                           form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html',
                                   title='Проблемы с регистрацией',
                                   message='Пароли не совпадают',
                                   form=form)
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html',
                                   title='Проблемы с регистрацией',
                                   message='Такой пользователь уже есть',
                                   form=form)
        user = User(name=form.name.data,
                    email=form.email.data,
                    about=form.about.data)
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect('/')
        return render_template('login.html', title='Повторная авторизация',
                               message='Неверный логин или пароль',
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)



@app.route('/weather_form', methods=['GET', 'POST'])
def weather_form():
    if request.method == 'GET':
        return render_template('weather_form.html',
                               title='Выбор города')
    elif request.method == 'POST':
        town = request.form.get('town')
        data = {}
        key = '78104c7cf846b04c6e7f47d241f9bb7e'
        url = 'http://api.openweathermap.org/data/2.5/weather'
        params = {'APPID': key, 'q': town, 'units': 'metric'}
        result = requests.get(url, params=params)
        weather = result.json()
        code = weather['cod']
        icon = weather['weather'][0]['icon']
        temperature = weather['main']['temp']
        data['code'] = code
        data['icon'] = icon
        data['temp'] = temperature
        return render_template('weather.html',
                               title=f'Погода в городе {town}',
                               town=town, data=weather,
                               icon=icon)



#
# @app.route('/weather_form', methods=['GET', 'POST'])
# def weather_form():
#     if request.method == 'GET':
#         return render_template('weather_form.html',
#                                title='Выбор города')
#     elif request.method == 'POST':
#         town = request.form.get('town')
#         if not town.strip():
#             town = 'Москва'
#         data = {}
#         key = 'c747bf84924be997ff13ac5034fa3f86'
#         url = 'http://api.openweathermap.org/data/2.5/weather'
#         params = {'APPID': key, 'q': town, 'units': 'metric'}
#         result = requests.get(url, params=params)
#         weather = result.json()
#         code = weather['cod']
#         icon = weather['weather'][0]['icon']
#         temperature = weather['main']['temp']
#         data['code'] = code
#         data['icon'] = icon
#         data['temp'] = temperature
#         return render_template('weather.html',
#                                title=f'Погода в городе {town}',
#                                town=town, data=data)


@app.route('/form_sample', methods=['GET', 'POST'])
def form_sample():
    if request.method == 'GET':
        return render_template('user_form.html', title='Форма')
    elif request.method == 'POST':
        f = request.files['file']  # request.form.get('file')
        f.save('./static/images/loaded.png')
        myform = request.form.to_dict()
        return render_template('filled_form.html',
                               title='Ваши данные',
                               data=myform)



@app.route('/cookie_test')
def cookie_test():
    visit_count = int(request.cookies.get('visit_count', 0))
    if visit_count != 0 and visit_count <= 20:
        res = make_response(f'Были уже {visit_count + 1} раз')
        res.set_cookie('visit_count',
                       str(visit_count + 1),
                       max_age=60 * 60 * 24 * 365 * 2)
    elif visit_count > 20:
        print('Мы тут')
        res = make_response(f'Были уже {visit_count + 1} раз')
        res.set_cookie('visit_count', '1', max_age=0)
    else:
        res = make_response('Вы впервые здесь за 2 года')
        res.set_cookie('visit_count', '1',
                       max_age=60 * 60 * 24 * 365 * 2)
    return res


# Let's Encrypt
@app.route('/session_test')
def session_test():
    visit_count = session.get('visit_count', 0)
    session['visit_count'] = visit_count + 1
    if session['visit_count'] > 3:
        session.pop('visit_count', None)
    session.permanent = True  # Максимум 31 день
    return make_response(f'Мы тут были уже {visit_count + 1} раз.')



if __name__ == '__main__':
    db_session.global_init('db/news.sqlite')
    app.run(host='127.0.0.1', port=5000, debug=True)
