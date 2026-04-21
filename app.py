import os
import requests  

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from models import db, User, Party, Ticket, Review, Message
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

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
        print("✅ Админ создан (логин: admin, пароль: admin)")

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
        print("✅ Созданы тестовые вечеринки")

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
            return redirect(url_for('premium'))
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

# ---------- Регистрация ----------
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

# ---------- Профиль ----------
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

# ---------- Вечеринки ----------
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

# 🔥 ДЕТАЛИ ВЕЧЕРИНКИ
@app.route('/party/<int:party_id>')
def party_detail(party_id):
    party = Party.query.get_or_404(party_id)
    return render_template('party_detail.html', party=party)

# ---------- Премиум ----------
@app.route('/premium')
def premium():
    """Страница премиум подписки"""
    return render_template('premium.html')

@app.route('/buy_premium', methods=['POST'])
@login_required
def buy_premium():
    """Активация премиум подписки"""
    user = User.query.get(session['user_id'])
    if user:
        user.is_premium = True
        db.session.commit()
        flash('🎉 Премиум успешно активирован! Теперь вы можете создавать вечеринки.', 'success')
    else:
        flash('Пользователь не найден', 'error')
    return redirect(url_for('profile', user_id=user.id))

# ---------- Создание вечеринки ----------
@app.route('/create_party', methods=['GET', 'POST'])
@premium_required
def create_party():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        city = request.form.get('city')
        location = request.form.get('location', '')
        date_str = request.form.get('date')
        min_age = int(request.form.get('min_age', 18))
        theme = request.form.get('theme')
        genre = request.form.get('genre')
        photo_url = request.form.get('photo_url', '')

        # 🔥 ВАЖНО — исправлено имя
        ticket_price = float(request.form.get('ticket_price', 0))
        total_tickets = int(request.form.get('total_tickets', 0))

        try:
            date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('❌ Неверный формат даты', 'danger')
            return redirect(url_for('create_party'))

        party = Party(
            title=title,
            description=description,
            city=city,
            location=location,
            date=date,
            min_age=min_age,
            theme=theme,
            genre=genre,
            photo_url=photo_url,
            ticket_price=ticket_price,
            total_tickets=total_tickets,
            available_tickets=total_tickets,
            organizer_id=session['user_id'],
            status='pending'
        )

        db.session.add(party)
        db.session.commit()

        # 🔥 ОТПРАВКА В TELEGRAM
        send_to_telegram(
            f"🆕 Новая вечеринка!\n\n"
            f"🎉 {title}\n"
            f"📍 {city}\n"
            f"📅 {date.strftime('%d.%m.%Y %H:%M')}",
            party.id
        )

        flash('Вечеринка отправлена на модерацию', 'info')
        return redirect(url_for('parties'))

    genres_list = ['Хаус', 'Техно', 'Поп', 'Рок', 'Костюмированная', 'Корпоратив', 'Другое']
    return render_template('create_party.html', genres=genres_list)

# 🔥 ПОКУПКА БИЛЕТА (ПОКА БЕЗ СОХРАНЕНИЯ)
@app.route('/purchase/<int:party_id>', methods=['GET', 'POST'])
def purchase(party_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    party = Party.query.get_or_404(party_id)

    if request.method == 'POST':
        flash('✅ Покупка прошла (пока без сохранения)')
        return redirect(url_for('my_tickets'))

    return render_template('purchase.html', party=party)

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    data = request.json

    if "callback_query" in data:
        callback = data["callback_query"]
        action = callback["data"]

        if action.startswith("approve_"):
            party_id = int(action.split("_")[1])
            party = Party.query.get(party_id)
            if party:
                party.status = "approved"
                db.session.commit()

        elif action.startswith("reject_"):
            party_id = int(action.split("_")[1])
            party = Party.query.get(party_id)
            if party:
                party.status = "rejected"
                db.session.commit()

    return "ok"


# 🔥 МОИ БИЛЕТЫ
@app.route('/my-tickets')
def my_tickets():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')

    tickets = Ticket.query.filter_by(user_id=user_id).all()

    return render_template('my_tickets.html', tickets=tickets)

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
    flash('Билет возвращён.', 'info')
    return redirect(url_for('my_tickets'))

# ---------- Отзывы ----------
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
    flash('Отзыв добавлен!', 'success')
    return redirect(url_for('party_detail', party_id=party_id))

# ---------- Админка ----------
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

def send_to_telegram(text, party_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    approve_url = f"http://127.0.0.1:5000/admin/approve/{party_id}"
    reject_url = f"http://127.0.0.1:5000/admin/reject/{party_id}"

    full_text = (
        text +
        "\n\n"
        f"✅ Одобрить:\n{approve_url}\n\n"
        f"❌ Отклонить:\n{reject_url}"
    )

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": full_text
    })

@app.route('/admin/reject/<int:party_id>', methods=['GET', 'POST'])
@admin_required
def reject_party(party_id):
    party = Party.query.get_or_404(party_id)

    if request.method == 'POST':
        reason = request.form.get('reason')

        party.status = 'rejected'
        party.rejection_reason = reason

        db.session.commit()

        flash('Вечеринка отклонена', 'warning')
        return redirect(url_for('admin_parties'))

    return render_template('reject_party.html', party=party)

# ---------- Контекстный процессор ----------
@app.context_processor
def utility_processor():
    def get_user(user_id):
        return User.query.get(user_id)
    return dict(get_user=get_user)

if __name__ == '__main__':
    app.run(debug=True)