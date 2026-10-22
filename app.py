import os
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from sqlalchemy.exc import IntegrityError
from email_validator import validate_email, EmailNotValidError

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def parse_datetime(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("must be an ISO-8601 date/time string")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        raise ValueError("must be a valid ISO-8601 date/time string")

class Supermarket(db.Model):
    __tablename__ = "supermarkets"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    offers = db.relationship("Offer", backref="supermarket", cascade="all, delete-orphan")

class Offer(db.Model):
    __tablename__ = "offers"
    id = db.Column(db.Integer, primary_key=True)
    supermarket_id = db.Column(db.Integer, db.ForeignKey("supermarkets.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, index=True)
    end_date = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "supermarket_id": self.supermarket_id,
            "supermarket_name": self.supermarket.name,
            "title": self.title,
            "description": self.description,
            "discount_percent": float(self.discount_percent),
            "start_date": self.start_date.isoformat() + "Z",
            "end_date": self.end_date.isoformat() + "Z",
            "created_at": self.created_at.isoformat() + "Z",
        }

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        JWT_SECRET=os.environ.get("JWT_SECRET", os.environ.get("SECRET_KEY", "dev-only-change-me")),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///offers.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    def error(message, status):
        return jsonify({"error": message}), status

    def token_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return error("Bearer token required", 401)
            token = header.split(" ", 1)[1].strip()
            try:
                payload = jwt.decode(token, app.config["JWT_SECRET"], algorithms=["HS256"])
                owner_id = int(payload["sub"])
            except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
                return error("Invalid or expired token", 401)
            owner = db.session.get(Supermarket, owner_id)
            if owner is None:
                return error("Account no longer exists", 401)
            request.current_supermarket = owner
            return fn(*args, **kwargs)
        return wrapper

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/supermarkets")
    def register_supermarket():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("Request body must be a JSON object", 400)
        required = ("name", "email", "password", "address")
        missing = [key for key in required if not isinstance(data.get(key), str) or not data[key].strip()]
        if missing:
            return error("Required non-empty fields: " + ", ".join(missing), 400)
        name, email, password, address = (data[k].strip() for k in required)
        if len(name) > 150 or len(email) > 255 or len(address) > 2000:
            return error("One or more fields exceed the allowed length", 400)
        if len(password) < 8:
            return error("Password must be at least 8 characters", 400)
        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            return error("A valid email address is required", 400)
        phone = data.get("phone")
        if phone is not None and (not isinstance(phone, str) or len(phone) > 20):
            return error("Phone must be a string of at most 20 characters", 400)
        supermarket = Supermarket(
            name=name, email=email, password_hash=generate_password_hash(password),
            address=address, phone=phone.strip() if phone else None
        )
        db.session.add(supermarket)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return error("A supermarket with this email already exists", 409)
        return jsonify({
            "message": "Supermarket registered successfully",
            "supermarket": {"id": supermarket.id, "name": supermarket.name, "email": supermarket.email}
        }), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("Request body must be a JSON object", 400)
        email, password = data.get("email"), data.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            return error("Email and password are required", 400)
        owner = Supermarket.query.filter_by(email=email.strip().lower()).first()
        if owner is None or not check_password_hash(owner.password_hash, password):
            return error("Invalid email or password", 401)
        token = jwt.encode(
            {"sub": str(owner.id), "exp": datetime.now(timezone.utc) + timedelta(hours=2)},
            app.config["JWT_SECRET"], algorithm="HS256"
        )
        return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": 7200})

    @app.post("/api/supermarkets/<int:supermarket_id>/offers")
    @token_required
    def create_offer(supermarket_id):
        owner = request.current_supermarket
        if owner.id != supermarket_id:
            return error("You can only create offers for your own supermarket", 403)
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("Request body must be a JSON object", 400)
        title = data.get("title")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 200:
            return error("Title is required and must be at most 200 characters", 400)
        description = data.get("description", "")
        if description is not None and (not isinstance(description, str) or len(description) > 5000):
            return error("Description must be a string of at most 5000 characters", 400)
        try:
            discount = float(data.get("discount_percent"))
        except (TypeError, ValueError):
            return error("discount_percent must be a number between 0 and 100", 400)
        if not 0 < discount <= 100:
            return error("discount_percent must be greater than 0 and at most 100", 400)
        try:
            start_date = parse_datetime(data.get("start_date"))
            end_date = parse_datetime(data.get("end_date"))
        except ValueError as exc:
            return error(f"Invalid date: {exc}", 400)
        if end_date <= start_date:
            return error("end_date must be later than start_date", 400)
        offer = Offer(
            supermarket_id=owner.id, title=title.strip(),
            description=(description or "").strip(),
            discount_percent=round(discount, 2),
            start_date=start_date, end_date=end_date
        )
        db.session.add(offer)
        db.session.commit()
        return jsonify({"message": "Offer created successfully", "offer": offer.as_dict()}), 201

    @app.get("/api/offers")
    def browse_offers():
        now = utcnow()
        query = Offer.query.join(Supermarket).filter(
            Offer.start_date <= now, Offer.end_date >= now
        )
        supermarket_id = request.args.get("supermarket_id")
        if supermarket_id:
            try:
                query = query.filter(Offer.supermarket_id == int(supermarket_id))
            except ValueError:
                return error("supermarket_id must be an integer", 400)
        min_discount = request.args.get("min_discount")
        if min_discount is not None:
            try:
                minimum = float(min_discount)
                if not 0 <= minimum <= 100:
                    raise ValueError
            except ValueError:
                return error("min_discount must be a number between 0 and 100", 400)
            query = query.filter(Offer.discount_percent >= minimum)
        search = request.args.get("q", "").strip()
        if len(search) > 100:
            return error("Search query must be at most 100 characters", 400)
        if search:
            pattern = f"%{search}%"
            query = query.filter(db.or_(Offer.title.ilike(pattern), Offer.description.ilike(pattern),
                                        Supermarket.name.ilike(pattern)))
        try:
            page = max(1, int(request.args.get("page", "1")))
            limit = int(request.args.get("limit", "10"))
            if limit < 1 or limit > 100:
                raise ValueError
        except ValueError:
            return error("page must be positive and limit must be between 1 and 100", 400)
        pagination = query.order_by(Offer.end_date.asc()).paginate(
            page=page, per_page=limit, error_out=False
        )
        return jsonify({
            "page": page, "limit": limit, "total": pagination.total,
            "pages": pagination.pages,
            "offers": [offer.as_dict() for offer in pagination.items]
        })

    @app.get("/api/supermarkets")
    def list_supermarkets():
        rows = Supermarket.query.order_by(Supermarket.name.asc()).all()
        return jsonify({"supermarkets": [
            {"id": row.id, "name": row.name, "address": row.address}
            for row in rows
        ]})

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found"}), 404
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(_):
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
