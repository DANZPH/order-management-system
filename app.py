from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import qrcode
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    order_received = db.Column(db.Boolean, default=False)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    orders = Order.query.all()
    return render_template('index.html', orders=orders)

@app.route('/add_item', methods=['POST'])
def add_item():
    item_name = request.form['item_name']
    new_order = Order(item_name=item_name)
    db.session.add(new_order)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/checkout/<int:order_id>')
def checkout(order_id):
    order = Order.query.get(order_id)
    if order and not order.order_received:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(order.id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_path = f'static/qrcodes/{order.id}.png'
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        img.save(img_path)
        return render_template('checkout.html', order=order, img_path=img_path)
    elif order and order.order_received:
        return "Order has already been received."
    else:
        return "Order not found."

@app.route('/scanner/<int:order_id>')
def scanner(order_id):
    return render_template('scanner.html', order_id=order_id)

@app.route('/upload_scan/<int:order_id>', methods=['POST'])
def upload_scan(order_id):
    order = Order.query.get(order_id)
    if order:
        uploaded_file = request.files['file']
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)
            scanned_data = process_uploaded_file(file_path)
            if str(order.id) == scanned_data:
                order.order_received = True
                db.session.commit()
                return jsonify({'message': 'Scan successful. Order received!'}), 200
            else:
                return jsonify({'message': 'Scan unsuccessful. Invalid data.'}), 400
        else:
            return jsonify({'message': 'Invalid file format or no file provided.'}), 400
    else:
        return jsonify({'message': 'Scan unsuccessful. Order not found.'}), 404

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_uploaded_file(file_path):
    _, filename = os.path.split(file_path)
    return os.path.splitext(filename)[0]

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
()