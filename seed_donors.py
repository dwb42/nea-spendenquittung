"""Seed the database with initial donor data."""
import sys
sys.path.insert(0, ".")
from backend.database import get_db, init_db

donors = [
    ("Gerd Haas", "Grüner Weg 24", "48599", "Gronau"),
    ("Axel Hansing", "Lindenstr. 22", "8832", "Wollerau, Schweiz"),
    ("Annkathrin Heydenreich", "Rodewalder Str. 10", "29690", "Gilten"),
    ("Gabriele Heydenreich", "Rodewalder Str. 10", "29690", "Gilten"),
    ("Hajo Heydenreich", "Rodewalder Str. 10", "29690", "Gilten"),
    ("Bernd Kamphuis", "Gräfeheid 7", "56130", "Bad Ems"),
    ("Christiane Siebert", "Allerweg 25", "29690", "Buchholz/Aller"),
    ("Peter Vogel", "Hoyaer Str. 45", "31608", "Marklohe"),
    ("Felix Wilmes", "Zenettistr. 34", "80337", "München"),
    ("Achim Witte", "Stemmer Str. 23", "31655", "Stadthagen / Hobbensen"),
    ("Ingo Wojtynia", "Bornholzweg 93", "32457", "Porta Westfalica"),
    ("Thilo u. Claudia Jakob", "Kaspersweg 44b", "26131", "Oldenburg"),
    ("Hendrike Heydenreich", "Witts Allee 34", "22587", "Hamburg"),
    ("Holger Laatsch", "Kastanienweg 7b", "18465", "Tribsees"),
    ("Bernd Kamphuis", "Plankstraße 87", "45147", "Essen"),
    ("Peter Otremba", "Hirtenweg 1", "29690", "Büchten"),
    ("Sebastian Mühlon", "Kutzenberg 31a", "96250", "Ebensfeld"),
    ("Dietrich Wedegärtner", "Thadenstr. 160a", "22767", "Hamburg"),
    ("Beate Dr. Lindemann", "Winkler Str. 22", "14193", "Berlin"),
    ("Hinrich Christophers", "Feldbrunnenstr. 40", "20148", "Hamburg"),
]

init_db()
db = get_db()

# Clear existing donors
db.execute("DELETE FROM donors")

for name, strasse, plz, ort in donors:
    db.execute(
        "INSERT INTO donors (name, strasse, plz, ort) VALUES (?, ?, ?, ?)",
        (name, strasse, plz, ort),
    )

db.commit()
print(f"Inserted {len(donors)} donors.")
db.close()
