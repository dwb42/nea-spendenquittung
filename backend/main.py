import os
import secrets
from datetime import datetime, date
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from .database import get_db, init_db
from .pdf_generator import generate_pdf, format_betrag
from .email_service import send_receipt_email

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

APP_PASSWORD = os.getenv("APP_PASSWORD", "mateke")
EMAIL_DEFAULT_TO = os.getenv("EMAIL_DEFAULT_TO", "Post@heydenreichprojekte.de")

app = FastAPI()

# Session store (in-memory, simple)
sessions: dict[str, bool] = {}

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


# --- Auth ---

class LoginRequest(BaseModel):
    password: str


def require_auth(request: Request):
    token = request.cookies.get("session")
    if not token or token not in sessions:
        raise HTTPException(status_code=401, detail="Nicht autorisiert")


@app.post("/api/login")
def login(req: LoginRequest, response: Response):
    if req.password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Falsches Passwort")
    token = secrets.token_hex(32)
    sessions[token] = True
    response.set_cookie("session", token, httponly=True, samesite="strict", max_age=86400)
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session")
    if token:
        sessions.pop(token, None)
    response.delete_cookie("session")
    return {"ok": True}


@app.get("/api/auth/check")
def auth_check(request: Request):
    token = request.cookies.get("session")
    if token and token in sessions:
        return {"authenticated": True}
    return {"authenticated": False}


# --- Donors ---

class DonorCreate(BaseModel):
    name: str
    strasse: str
    plz: str
    ort: str


class DonorUpdate(BaseModel):
    name: str
    strasse: str
    plz: str
    ort: str


@app.get("/api/donors")
def list_donors(_=Depends(require_auth)):
    db = get_db()
    rows = db.execute("SELECT * FROM donors ORDER BY name").fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.post("/api/donors")
def create_donor(donor: DonorCreate, _=Depends(require_auth)):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO donors (name, strasse, plz, ort) VALUES (?, ?, ?, ?)",
        (donor.name, donor.strasse, donor.plz, donor.ort),
    )
    db.commit()
    donor_id = cursor.lastrowid
    row = db.execute("SELECT * FROM donors WHERE id = ?", (donor_id,)).fetchone()
    db.close()
    return dict(row)


@app.put("/api/donors/{donor_id}")
def update_donor(donor_id: int, donor: DonorUpdate, _=Depends(require_auth)):
    db = get_db()
    db.execute(
        "UPDATE donors SET name=?, strasse=?, plz=?, ort=? WHERE id=?",
        (donor.name, donor.strasse, donor.plz, donor.ort, donor_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM donors WHERE id = ?", (donor_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Spender nicht gefunden")
    return dict(row)


@app.delete("/api/donors/{donor_id}")
def delete_donor(donor_id: int, _=Depends(require_auth)):
    db = get_db()
    db.execute("DELETE FROM donors WHERE id = ?", (donor_id,))
    db.commit()
    db.close()
    return {"ok": True}


# --- Receipts ---

class ReceiptCreate(BaseModel):
    donor_id: int
    betrag: float
    spendendatum: Optional[str] = None
    email: Optional[str] = None


@app.post("/api/receipts")
def create_receipt(req: ReceiptCreate, _=Depends(require_auth)):
    db = get_db()
    donor = db.execute("SELECT * FROM donors WHERE id = ?", (req.donor_id,)).fetchone()
    if not donor:
        db.close()
        raise HTTPException(status_code=404, detail="Spender nicht gefunden")

    spendendatum = req.spendendatum or date.today().strftime("%d.%m.%Y")
    email = req.email or EMAIL_DEFAULT_TO
    heute = date.today().strftime("%d.%m.%Y")

    # Generate PDF
    pdf_bytes = generate_pdf(
        donor_name=donor["name"],
        donor_strasse=donor["strasse"],
        donor_plz=donor["plz"],
        donor_ort=donor["ort"],
        betrag=req.betrag,
        spendendatum=spendendatum,
        unterschrift_datum=heute,
    )

    # Save to DB
    cursor = db.execute(
        "INSERT INTO receipts (donor_id, betrag, spendendatum, email, pdf) VALUES (?, ?, ?, ?, ?)",
        (req.donor_id, req.betrag, spendendatum, email, pdf_bytes),
    )
    db.commit()
    receipt_id = cursor.lastrowid

    db.close()
    return {
        "id": receipt_id,
        "donor_name": donor["name"],
        "betrag": req.betrag,
        "spendendatum": spendendatum,
        "email": email,
    }


class SendEmailRequest(BaseModel):
    email: Optional[str] = None


@app.post("/api/receipts/{receipt_id}/send")
def send_receipt(receipt_id: int, req: SendEmailRequest, _=Depends(require_auth)):
    db = get_db()
    row = db.execute("""
        SELECT r.*, d.name as donor_name
        FROM receipts r JOIN donors d ON r.donor_id = d.id
        WHERE r.id = ?
    """, (receipt_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Quittung nicht gefunden")

    to_email = req.email or row["email"]
    try:
        result = send_receipt_email(
            to_email=to_email,
            donor_name=row["donor_name"],
            betrag=format_betrag(row["betrag"]),
            spendendatum=row["spendendatum"],
            pdf_bytes=row["pdf"],
        )
        return {"ok": True, "email": to_email, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/receipts")
def list_receipts(_=Depends(require_auth)):
    db = get_db()
    rows = db.execute("""
        SELECT r.id, r.betrag, r.spendendatum, r.email, r.erstellt_am, d.name as donor_name
        FROM receipts r JOIN donors d ON r.donor_id = d.id
        ORDER BY r.erstellt_am DESC
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.get("/api/receipts/{receipt_id}/pdf")
def get_receipt_pdf(receipt_id: int, _=Depends(require_auth)):
    db = get_db()
    row = db.execute("""
        SELECT r.pdf, r.spendendatum, d.name as donor_name
        FROM receipts r JOIN donors d ON r.donor_id = d.id
        WHERE r.id = ?
    """, (receipt_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Quittung nicht gefunden")
    filename = f"Zuwendungsbestaetigung_{row['donor_name'].replace(' ', '_')}_{row['spendendatum'].replace('.', '')}.pdf"
    return Response(
        content=row["pdf"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# --- Config endpoint ---

@app.get("/api/config")
def get_config(_=Depends(require_auth)):
    return {"default_email": EMAIL_DEFAULT_TO}


# --- Serve frontend ---

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# --- Startup ---

@app.on_event("startup")
def on_startup():
    init_db()
