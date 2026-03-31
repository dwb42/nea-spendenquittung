import io
import os
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject, TextStringObject, BooleanObject

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "template.pdf")


def betrag_in_buchstaben(betrag: float) -> str:
    """Convert a numeric amount to German words."""
    einheiten = [
        "", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht",
        "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn",
        "sechzehn", "siebzehn", "achtzehn", "neunzehn",
    ]
    zehner = [
        "", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig",
        "siebzig", "achtzig", "neunzig",
    ]

    def unter_tausend(n: int) -> str:
        if n == 0:
            return ""
        if n < 20:
            return einheiten[n]
        if n < 100:
            e = n % 10
            z = n // 10
            if e == 0:
                return zehner[z]
            return einheiten[e] + "und" + zehner[z]
        h = n // 100
        rest = n % 100
        result = einheiten[h] + "hundert"
        if rest > 0:
            result += unter_tausend(rest)
        return result

    ganzzahl = int(betrag)
    cent = round((betrag - ganzzahl) * 100)

    if ganzzahl == 0:
        result = "null"
    elif ganzzahl == 1:
        result = "eins"
    else:
        parts = []
        if ganzzahl >= 1_000_000:
            millionen = ganzzahl // 1_000_000
            ganzzahl %= 1_000_000
            if millionen == 1:
                parts.append("eineMillion")
            else:
                parts.append(unter_tausend(millionen) + "Millionen")
        if ganzzahl >= 1000:
            tausender = ganzzahl // 1000
            ganzzahl %= 1000
            if tausender == 1:
                parts.append("eintausend")
            else:
                parts.append(unter_tausend(tausender) + "tausend")
        if ganzzahl > 0:
            parts.append(unter_tausend(ganzzahl))

        result = "".join(parts)

    # Capitalize first letter
    result = result[0].upper() + result[1:] if result else result

    if cent > 0:
        result += f" und {cent}/100"

    return result


def format_betrag(betrag: float) -> str:
    """Format amount as German currency string, e.g. 2.000,-"""
    ganzzahl = int(betrag)
    cent = round((betrag - ganzzahl) * 100)
    formatted = f"{ganzzahl:,.0f}".replace(",", ".")
    if cent > 0:
        return f"{formatted},{cent:02d}"
    return f"{formatted},-"


def generate_pdf(
    donor_name: str,
    donor_strasse: str,
    donor_plz: str,
    donor_ort: str,
    betrag: float,
    spendendatum: str,
    unterschrift_datum: str,
) -> bytes:
    """Fill the PDF template with donation data and return flattened PDF bytes."""
    reader = PdfReader(TEMPLATE_PATH)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    # Build the address block
    anschrift = f"{donor_name}\n{donor_strasse}, {donor_plz} {donor_ort}"

    # Field values to fill
    field_values = {
        "Name und Anschrift des Zuwendenden": anschrift,
        "Betrag der Zuwendung in Ziffern": format_betrag(betrag),
        "in Buchstaben": betrag_in_buchstaben(betrag),
        "Tag der Zuwendung": spendendatum,
        "Ort Datum und Unterschrift des Zuwendungsempfängers": f"Hamburg, den {unterschrift_datum}",
    }

    # Update form fields directly via AcroForm
    acroform = writer._root_object["/AcroForm"]
    for field_ref in acroform["/Fields"]:
        field = field_ref.get_object()
        field_name = field.get("/T", "")
        if field_name in field_values:
            field[NameObject("/V")] = TextStringObject(field_values[field_name])
            if "/AP" in field:
                del field["/AP"]

    # Tell PDF readers to regenerate appearances from /V values
    acroform[NameObject("/NeedAppearances")] = BooleanObject(True)

    # Also update annotations on page and set read-only
    for page in writer.pages:
        if "/Annots" in page:
            for annot in page["/Annots"]:
                annot_obj = annot.get_object()
                field_name = annot_obj.get("/T", "")
                if field_name in field_values:
                    annot_obj[NameObject("/V")] = TextStringObject(field_values[field_name])
                    if "/AP" in annot_obj:
                        del annot_obj["/AP"]
                # Set read-only flag
                if "/Ff" in annot_obj:
                    annot_obj[NameObject("/Ff")] = NumberObject(int(annot_obj["/Ff"]) | 1)
                else:
                    annot_obj[NameObject("/Ff")] = NumberObject(1)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
