import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from models import db, User, Party, Ticket, Review, Message
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tusa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

db.init_app(app)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', city='System', age=18, is_premium=True, is_admin=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()

    # Создание тестовых вечеринок, если их нет
    if Party.query.count() == 0:
        test_parties = [
            Party(
                title="Хаус вечеринка в центре",
                description="Крутая хаус тусовка с лучшими диджеями. Дресс-код: белый.",
                city="Москва",
                location="Тверская ул., 12",
                date=datetime(2026, 4, 20, 22, 0),
                min_age=18,
                theme="Хаус",
                genre="Хаус",
                photo_url="https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=400",
                ticket_price=1200,
                total_tickets=100,
                available_tickets=100,
                organizer_id=1,
                status='approved'
            ),
            Party(
                title="Техно рейв на заводе",
                description="Ночной техно рейв в заброшенном здании. Своя атмосфера.",
                city="Санкт-Петербург",
                location="Заводской пр., 5",
                date=datetime(2026, 4, 25, 23, 30),
                min_age=21,
                theme="Техно",
                genre="Техно",
                photo_url="https://images.unsplash.com/photo-1571512595597-3936b7b1b0f0?w=400",
                ticket_price=800,
                total_tickets=80,
                available_tickets=80,
                organizer_id=1,
                status='approved'
            ),
            Party(
                title="Поп-вечеринка 2000-х",
                description="Ностальгическая вечеринка с хитами нулевых. Караоке, конкурсы.",
                city="Казань",
                location="Баумана, 20",
                date=datetime(2026, 5, 1, 20, 0),
                min_age=18,
                theme="Поп",
                genre="Поп",
                photo_url="https://images.unsplash.com/photo-1524368535928-5b5e00ddc76b?w=400",
                ticket_price=500,
                total_tickets=150,
                available_tickets=150,
                organizer_id=1,
                status='approved'
            ),
            Party(
                title="Костюмированная вечеринка 'Гэтсби'",
                description="Стиль 20-х годов, джаз, шампанское. Приходи в образе.",
                city="Екатеринбург",
                location="Ленина, 45",
                date=datetime(2026, 5, 10, 19, 0),
                min_age=18,
                theme="Костюмированная",
                genre="Костюмированная",
                photo_url="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=400",
                ticket_price=1500,
                total_tickets=60,
                available_tickets=60,
                organizer_id=1,
                status='approved'
            )
        ]
        db.session.add_all(test_parties)
        db.session.commit()
        print("Созданы тестовые вечеринки")

# ---------- Декораторы ----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def premium_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Войдите', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_premium:
            flash('Только премиум-подписчики могут создавать вечеринки', 'danger')
            return redirect(url_for('parties'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Войдите', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Доступ только для администратора', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ---------- Главная ----------
@app.route('/')
def index():
    parties = Party.query.filter(Party.status == 'approved', Party.date >= datetime.now()).order_by(Party.date).all()
    return render_template('index.html', parties=parties)

# ---------- Регистрация 2 шага с загрузкой аватара ----------
@app.route('/register/step1', methods=['GET', 'POST'])
def register_step1():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        city = request.form['city']
        age = int(request.form['age'])
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('register_step1'))
        session['reg_username'] = username
        session['reg_password'] = password
        session['reg_city'] = city
        session['reg_age'] = age
        return redirect(url_for('register_step2'))
    return render_template('register_step1.html')

@app.route('/register/step2', methods=['GET', 'POST'])
def register_step2():
    if 'reg_username' not in session:
        return redirect(url_for('register_step1'))
    if request.method == 'POST':
        bio = request.form.get('bio', '')
        interests = request.form.get('interests', '')
        avatar_file = request.files.get('avatar')
        avatar_filename = 'default.png'
        if avatar_file and allowed_file(avatar_file.filename):
            ext = avatar_file.filename.rsplit('.', 1)[1].lower()
            safe_name = secure_filename(session['reg_username'] + '_' + datetime.now().strftime('%Y%m%d%H%M%S') + '.' + ext)
            avatar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_name))
            avatar_filename = safe_name
        user = User(
            username=session['reg_username'],
            city=session['reg_city'],
            age=session['reg_age'],
            avatar=avatar_filename,
            bio=bio,
            interests=interests,
            is_premium=False
        )
        user.set_password(session['reg_password'])
        db.session.add(user)
        db.session.commit()
        for key in ['reg_username', 'reg_password', 'reg_city', 'reg_age']:
            session.pop(key, None)
        flash('Регистрация завершена! Теперь войдите.', 'success')
        return redirect(url_for('login'))
    return render_template('register_step2.html')

@app.route('/register')
def register_redirect():
    return redirect(url_for('register_step1'))

# ---------- Вход / Выход ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('parties'))
        flash('Неверные данные', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли', 'info')
    return redirect(url_for('index'))

# ---------- Профиль пользователя ----------
@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    if 'user_id' not in session or (session['user_id'] != user_id and not User.query.get(session['user_id']).is_admin):
        flash('У вас нет доступа к этому профилю', 'danger')
        return redirect(url_for('index'))
    tickets = Ticket.query.filter_by(buyer_id=user_id).all()
    created_parties = Party.query.filter_by(organizer_id=user_id).all()
    return render_template('profile.html', user=user, tickets=tickets, created_parties=created_parties)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.city = request.form['city']
        user.age = int(request.form['age'])
        user.bio = request.form['bio']
        user.interests = request.form['interests']
        avatar_file = request.files.get('avatar')
        if avatar_file and allowed_file(avatar_file.filename):
            ext = avatar_file.filename.rsplit('.', 1)[1].lower()
            safe_name = secure_filename(f"{user.username}_edit_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
            avatar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_name))
            user.avatar = safe_name
        db.session.commit()
        flash('Профиль обновлён', 'success')
        return redirect(url_for('profile', user_id=user.id))
    return render_template('edit_profile.html', user=user)

# ---------- Список вечеринок с фильтрами ----------
@app.route('/parties')
def parties():
    city_filter = request.args.get('city', '')
    age_filter = request.args.get('age', type=int)
    genre_filter = request.args.get('genre', '')
    query = Party.query.filter(Party.status == 'approved', Party.date >= datetime.now())
    if city_filter:
        query = query.filter(Party.city == city_filter)
    if age_filter:
        query = query.filter(Party.min_age <= age_filter)
    if genre_filter:
        query = query.filter(Party.genre == genre_filter)
    parties = query.order_by(Party.date).all()
    cities = db.session.query(Party.city).distinct().filter(Party.status == 'approved').all()
    cities = [c[0] for c in cities if c[0]]
    genres = db.session.query(Party.genre).distinct().filter(Party.status == 'approved', Party.genre != None).all()
    genres = [g[0] for g in genres if g[0]]
    return render_template('parties.html', parties=parties, cities=cities, genres=genres,
                           selected_city=city_filter, selected_age=age_filter, selected_genre=genre_filter)

@app.route('/party/<int:party_id>')
def party_detail(party_id):
    party = Party.query.get_or_404(party_id)
    if party.status != 'approved' and not (session.get('user_id') and (User.query.get(session['user_id']).is_admin or party.organizer_id == session['user_id'])):
        flash('Вечеринка ещё не одобрена или отклонена', 'danger')
        return redirect(url_for('parties'))
    reviews = Review.query.filter_by(party_id=party_id).all()
    user = User.query.get(session['user_id']) if 'user_id' in session else None
    has_bought = False
    if user:
        has_bought = Ticket.query.filter_by(party_id=party_id, buyer_id=user.id).first() is not None
    return render_template('party_detail.html', party=party, reviews=reviews, user=user, has_bought=has_bought)

# ---------- Создание вечеринки (премиум) ----------
@app.route('/create_party', methods=['GET', 'POST'])
@premium_required
def create_party():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        city = request.form['city']
        location = request.form['location']
        date_str = request.form['date']
        min_age = int(request.form['min_age'])
        theme = request.form['theme']
        genre = request.form['genre']
        photo_url = request.form.get('photo_url', '')
        ticket_price = float(request.form['ticket_price'])
        total_tickets = int(request.form['total_tickets'])
        date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        party = Party(
            title=title, description=description, city=city, location=location,
            date=date, min_age=min_age, theme=theme, genre=genre, photo_url=photo_url,
            ticket_price=ticket_price, total_tickets=total_tickets,
            available_tickets=total_tickets, organizer_id=session['user_id'],
            status='pending'
        )
        db.session.add(party)
        db.session.commit()
        flash('Вечеринка отправлена на модерацию', 'info')
        return redirect(url_for('parties'))
    genres_list = ['Хаус', 'Техно', 'Поп', 'Рок', 'Костюмированная', 'Корпоратив', 'Другое']
    return render_template('create_party.html', genres=genres_list)

# ---------- Покупка билетов ----------
@app.route('/purchase/<int:party_id>', methods=['GET', 'POST'])
@login_required
def purchase(party_id):
    party = Party.query.get_or_404(party_id)
    user = User.query.get(session['user_id'])
    if party.status != 'approved':
        flash('Вечеринка недоступна для покупки', 'danger')
        return redirect(url_for('parties'))
    if user.age < party.min_age:
        flash(f'Нужно {party.min_age}+ лет', 'danger')
        return redirect(url_for('party_detail', party_id=party_id))
    if request.method == 'POST':
        quantity = int(request.form['quantity'])
        if quantity > party.available_tickets:
            flash(f'Доступно только {party.available_tickets} билетов', 'danger')
            return redirect(url_for('purchase', party_id=party_id))
        total = quantity * party.ticket_price
        for _ in range(quantity):
            ticket = Ticket(party_id=party.id, buyer_id=user.id, price=party.ticket_price)
            db.session.add(ticket)
        party.available_tickets -= quantity
        db.session.commit()
        flash(f'Куплено {quantity} билет(ов) на {party.title} за {total} руб.', 'success')
        return redirect(url_for('my_tickets'))
    return render_template('purchase.html', party=party)

@app.route('/my_tickets')
@login_required
def my_tickets():
    tickets = Ticket.query.filter_by(buyer_id=session['user_id']).all()
    return render_template('my_tickets.html', tickets=tickets, now=datetime.now())

@app.route('/my_parties')
@login_required
def my_parties():
    user = User.query.get(session['user_id'])
    parties = Party.query.filter_by(organizer_id=user.id).all()
    return render_template('my_parties.html', parties=parties)

@app.route('/cancel_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def cancel_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.buyer_id != session['user_id']:
        flash('Чужой билет', 'danger')
        return redirect(url_for('my_tickets'))
    if ticket.party.date < datetime.now():
        flash('Нельзя вернуть билет на прошедшую вечеринку', 'danger')
        return redirect(url_for('my_tickets'))
    party = ticket.party
    db.session.delete(ticket)
    party.available_tickets += 1
    db.session.commit()
    flash('Билет возвращён. Деньги вернутся в течение 5 дней (демо).', 'info')
    return redirect(url_for('my_tickets'))

@app.route('/review/<int:party_id>', methods=['POST'])
@login_required
def add_review(party_id):
    party = Party.query.get_or_404(party_id)
    bought = Ticket.query.filter_by(party_id=party_id, buyer_id=session['user_id']).first()
    if not bought:
        flash('Отзыв только после покупки билета', 'danger')
        return redirect(url_for('party_detail', party_id=party_id))
    rating = int(request.form['rating'])
    comment = request.form['comment']
    review = Review(party_id=party_id, user_id=session['user_id'], rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()
    flash('Отзыв добавлен, спасибо!', 'success')
    return redirect(url_for('party_detail', party_id=party_id))

@app.route('/chat/<int:party_id>', methods=['GET', 'POST'])
@login_required
def chat_organizer(party_id):
    party = Party.query.get_or_404(party_id)
    user = User.query.get(session['user_id'])
    if not (Ticket.query.filter_by(party_id=party_id, buyer_id=user.id).first() or party.organizer_id == user.id):
        flash('Вы можете общаться только если купили билет или вы организатор', 'danger')
        return redirect(url_for('party_detail', party_id=party_id))
    if request.method == 'POST':
        msg = request.form['message']
        if msg.strip():
            message = Message(party_id=party_id, from_user_id=user.id, to_user_id=party.organizer_id, message=msg)
            db.session.add(message)
            db.session.commit()
            flash('Сообщение отправлено', 'success')
        return redirect(url_for('chat_organizer', party_id=party_id))
    messages = Message.query.filter(
        ((Message.from_user_id == user.id) & (Message.to_user_id == party.organizer_id)) |
        ((Message.from_user_id == party.organizer_id) & (Message.to_user_id == user.id))
    ).order_by(Message.timestamp).all()
    return render_template('chat_organizer.html', party=party, messages=messages, user=user)

@app.route('/admin/parties')
@admin_required
def admin_parties():
    pending_parties = Party.query.filter_by(status='pending').order_by(Party.created_at).all()
    return render_template('admin_parties.html', parties=pending_parties)

@app.route('/admin/approve/<int:party_id>')
@admin_required
def approve_party(party_id):
    party = Party.query.get_or_404(party_id)
    party.status = 'approved'
    db.session.commit()
    flash(f'Вечеринка "{party.title}" одобрена', 'success')
    return redirect(url_for('admin_parties'))

@app.route('/admin/reject/<int:party_id>')
@admin_required
def reject_party(party_id):
    party = Party.query.get_or_404(party_id)
    party.status = 'rejected'
    db.session.commit()
    flash(f'Вечеринка "{party.title}" отклонена', 'warning')
    return redirect(url_for('admin_parties'))

# ---------- Контекстный процессор ----------
@app.context_processor
def utility_processor():
    def get_user(user_id):
        return User.query.get(user_id)
    return dict(get_user=get_user)

if __name__ == '__main__':
    app.run(debug=True)