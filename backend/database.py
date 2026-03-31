import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "spendenbeleg.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            strasse TEXT NOT NULL,
            plz TEXT NOT NULL,
            ort TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            betrag REAL NOT NULL,
            spendendatum TEXT NOT NULL,
            email TEXT NOT NULL,
            pdf BLOB NOT NULL,
            erstellt_am TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (donor_id) REFERENCES donors(id)
        );
    """)
    conn.commit()
    conn.close()
