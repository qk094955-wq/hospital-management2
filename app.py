"""
Hospital Management Dashboard (DEMONSTRATION PROJECT)
=====================================================
A beginner-friendly Streamlit application that manages patients, doctors,
appointments, billing/payments, hospital staff and inpatient admissions.

IMPORTANT
---------
* All people, phone numbers and e-mails are FICTIONAL sample data.
* All data lives in Streamlit session state (memory). It is TEMPORARY and is
  lost when the session resets or the deployed app restarts.
* The billing module is a demonstration only - it is NOT a payment processor.

Run locally with:   streamlit run app.py
"""

import random
import re
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration (must be the first Streamlit command)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Hospital Management Dashboard",
    page_icon="🏥",
    layout="wide",
)

S = st.session_state  # short alias used throughout the file

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CURRENCY = "$"
SLOT_MINUTES = 30  # every appointment lasts exactly 30 minutes
# Clinic hours: 09:00 - 17:00 -> 16 slots, last slot starts at 16:30
TIME_SLOTS = [
    f"{(9 * 60 + SLOT_MINUTES * i) // 60:02d}:{(9 * 60 + SLOT_MINUTES * i) % 60:02d}"
    for i in range(16)
]

GENDERS = ["Female", "Male", "Other"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
PATIENT_STATUSES = ["Active", "Inactive"]
AVAILABILITY = ["Available", "Busy", "On Leave"]
DOCTOR_EMPLOYMENT = ["Full-time", "Part-time", "Visiting", "Inactive"]
APPT_STATUSES = ["Scheduled", "Confirmed", "In Progress", "Completed", "Cancelled", "No Show"]
APPT_TYPES = ["Consultation", "Follow-up", "Check-up", "Procedure", "Emergency"]
PENDING_APPT_STATUSES = ("Scheduled", "Confirmed", "In Progress")
FREE_SLOT_STATUSES = ("Cancelled", "No Show")  # these statuses free the time slot
PAYMENT_METHODS = ["Cash", "Credit/Debit Card", "Bank Transfer", "Mobile Wallet", "Insurance"]
PAYMENT_STATUSES = ["Pending", "Completed", "Failed", "Refunded"]
# Allowed payment status changes (a finished payment can only be refunded)
PAYMENT_TRANSITIONS = {
    "Pending": ["Completed", "Failed"],
    "Completed": ["Refunded"],
    "Failed": [],
    "Refunded": [],
}
STAFF_STATUSES = ["Active", "On Leave", "Inactive"]
WARDS = ["General Ward", "ICU", "Maternity", "Pediatrics", "Surgical"]
ADMISSION_STATUSES = ["Admitted", "Discharged"]

STATUS_ICONS = {
    "Scheduled": "🔵", "Confirmed": "🟣", "In Progress": "🟠", "Completed": "🟢",
    "Cancelled": "🔴", "No Show": "⚫", "Pending": "🟠", "Failed": "🔴",
    "Refunded": "🟣", "Paid": "🟢", "Partially Paid": "🟠", "Unpaid": "🔴",
    "Active": "🟢", "Inactive": "⚫", "On Leave": "🟠", "Available": "🟢",
    "Busy": "🟠", "Admitted": "🔵", "Discharged": "🟢",
}
BADGE_COLUMNS = ["status", "payment_status", "availability", "employment_status"]

BLUES = ["#1f6fd1", "#4a90e2", "#14407a", "#7fb2ee", "#2c5aa0", "#a9cdf5", "#0b2a55", "#5d9bd8"]

STORAGE_NOTICE = (
    "ℹ️ **Demo notice:** all data is kept in temporary session memory with fictional sample "
    "records. It is lost when your session resets or the deployed app restarts. "
    "The billing module is a demonstration only and is **not** a real payment processor."
)

PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{6,14}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


# ---------------------------------------------------------------------------
# Small generic helpers
# ---------------------------------------------------------------------------
def inject_css():
    """A little CSS for a clean blue/white/light-gray medical theme."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {background-color: #eaf2fb;}
        [data-testid="stSidebar"] * {color: #14407a;}
        div[data-testid="stMetric"] {
            background: #ffffff; border: 1px solid #d6e4f5; border-left: 5px solid #1f6fd1;
            padding: 10px 14px; border-radius: 10px;
        }
        div[data-testid="stMetric"] * {color: #1b2a41 !important;}
        h1, h2, h3 {color: #1f6fd1;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def money(value):
    """Format a number as currency."""
    return f"{CURRENCY}{float(value):,.2f}"


def flash(kind, message):
    """Queue a message that is displayed after the next rerun."""
    S.flash.append((kind, message))


def show_flash():
    for kind, message in S.flash:
        getattr(st, kind)(message)
    S.flash = []


def clear_keys(prefix):
    """Reset form widgets by removing their saved values."""
    for key in list(S.keys()):
        if isinstance(key, str) and key.startswith(prefix):
            del S[key]


def next_id(prefix, existing_ids):
    """Return the next free ID such as PAT-0021."""
    numbers = [int(i.split("-")[1]) for i in existing_ids if re.fullmatch(rf"{prefix}-\d+", i)]
    return f"{prefix}-{(max(numbers) + 1 if numbers else 1):04d}"


def resolve_id(entered, prefix, existing_ids):
    """Validate a manually typed ID or generate one if left blank.
    Returns (id, error_message)."""
    entered = entered.strip().upper()
    if not entered:
        return next_id(prefix, existing_ids), None
    if not re.fullmatch(rf"{prefix}-\d{{4}}", entered):
        return None, f"ID must look like {prefix}-0001 (prefix, dash, 4 digits)."
    if entered in existing_ids:
        return None, f"ID {entered} already exists. Choose a different ID or leave it blank."
    return entered, None


def valid_phone(value):
    return bool(PHONE_RE.match(value.strip()))


def valid_email(value):
    return bool(EMAIL_RE.match(value.strip()))


def validate_contact(phone, email):
    errors = []
    if not valid_phone(phone):
        errors.append("Phone number is invalid (use 7-15 digits, e.g. +1-555-123-4567).")
    if not valid_email(email):
        errors.append("Email address is invalid (e.g. name@example.com).")
    return errors


def calc_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def pretty(df):
    """Friendlier column titles for display and CSV files."""
    return df.rename(columns=lambda c: c.replace("_", " ").title().replace(" Id", " ID"))


def show_table(df, empty_message="No records to display."):
    """Display a searchable/sortable table with status icons."""
    if df.empty:
        st.info(empty_message)
        return
    view = df.copy()
    for col in BADGE_COLUMNS:
        if col in view.columns:
            view[col] = view[col].map(lambda v: f"{STATUS_ICONS[v]} {v}" if v in STATUS_ICONS else v)
    st.dataframe(pretty(view), hide_index=True)


def download_csv(df, label, filename, key):
    st.download_button(
        label,
        data=pretty(df).to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
        disabled=df.empty,
    )


def text_search(df, query, columns):
    """Case-insensitive search across several columns."""
    query = query.strip().lower()
    if not query or df.empty:
        return df
    mask = pd.Series(False, index=df.index)
    for col in columns:
        mask |= df[col].astype(str).str.lower().str.contains(query, regex=False)
    return df[mask]


def pick(df, column, selected):
    """Keep rows whose column is in the selected list (empty selection = all)."""
    if selected and not df.empty:
        return df[df[column].isin(selected)]
    return df


def filter_dates(df, column, start, end):
    """Keep rows whose date column is between start and end (inclusive)."""
    if df.empty:
        return df
    mask = df[column].map(lambda d: d is not None and start <= d <= end).astype(bool)
    return df[mask]


def date_range_inputs(prefix, default_start, default_end):
    """Two date pickers with validation. Returns (start, end) or (None, None)."""
    c1, c2 = st.columns(2)
    start = c1.date_input("From", value=default_start, key=f"{prefix}_from")
    end = c2.date_input("To", value=default_end, key=f"{prefix}_to")
    if start > end:
        st.error("The start date must be on or before the end date.")
        return None, None
    return start, end


def confirm_delete(key, label):
    """Checkbox + button. Returns True only when confirmed and clicked."""
    confirmed = st.checkbox(label, key=f"{key}_chk")
    return st.button("🗑️ Delete permanently", key=f"{key}_btn", disabled=not confirmed, type="primary")


def show_errors(errors):
    for message in errors:
        st.error(message)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def find(rows, key, value):
    for row in rows:
        if row[key] == value:
            return row
    return None


def patient_name(pid):
    p = find(S.patients, "patient_id", pid)
    return p["name"] if p else "Unknown"


def doctor_name(did):
    d = find(S.doctors, "doctor_id", did)
    return d["name"] if d else "Unknown"


def patient_labels():
    return {p["patient_id"]: f"{p['patient_id']} - {p['name']}" for p in S.patients}


def doctor_labels():
    return {d["doctor_id"]: f"{d['doctor_id']} - {d['name']} ({d['specialization']})" for d in S.doctors}


def appointment_labels():
    return {
        a["appointment_id"]: f"{a['appointment_id']} | {a['date']} {a['time']} | "
        f"{patient_name(a['patient_id'])} with {doctor_name(a['doctor_id'])} [{a['status']}]"
        for a in sorted(S.appointments, key=lambda a: (a["date"], a["time"]), reverse=True)
    }


# ---------------------------------------------------------------------------
# DataFrame builders (always return the same columns, even when empty)
# ---------------------------------------------------------------------------
def patients_df():
    cols = ["patient_id", "name", "age", "dob", "gender", "phone", "email", "address",
            "blood_group", "emergency_contact", "emergency_phone", "registration_date", "status"]
    rows = [dict(p, age=calc_age(p["dob"])) for p in S.patients]
    return pd.DataFrame(rows, columns=cols)


def doctors_df():
    cols = ["doctor_id", "name", "specialization", "department", "phone", "email",
            "consultation_fee", "availability", "experience_years", "employment_status"]
    return pd.DataFrame(S.doctors, columns=cols)


def staff_df():
    cols = ["staff_id", "name", "job_title", "department", "phone", "email",
            "monthly_salary", "joining_date", "status"]
    return pd.DataFrame(S.staff, columns=cols)


def appointments_df(rows=None):
    cols = ["appointment_id", "patient_id", "patient_name", "doctor_id", "doctor_name", "date",
            "time", "type", "fee", "status", "reason", "notes"]
    rows = S.appointments if rows is None else rows
    data = [dict(a, patient_name=patient_name(a["patient_id"]), doctor_name=doctor_name(a["doctor_id"]))
            for a in rows]
    df = pd.DataFrame(data, columns=cols)
    return df.sort_values(["date", "time"], ascending=False) if not df.empty else df


def invoices_df():
    cols = ["invoice_id", "patient_id", "patient_name", "appointment_id", "billing_date",
            "consultation", "medicine", "lab", "other", "total", "amount_paid", "balance",
            "payment_status"]
    data = [dict(i, patient_name=patient_name(i["patient_id"])) for i in S.invoices]
    df = pd.DataFrame(data, columns=cols)
    return df.sort_values("billing_date", ascending=False) if not df.empty else df


def payments_df():
    cols = ["payment_id", "invoice_id", "patient_id", "patient_name", "amount", "method",
            "payment_date", "status", "reference"]
    data = [dict(p, patient_name=patient_name(p["patient_id"])) for p in S.payments]
    df = pd.DataFrame(data, columns=cols)
    return df.sort_values("payment_date", ascending=False) if not df.empty else df


def length_of_stay(adm):
    """Days between admission and discharge (or today). Same-day stays count as 1 day."""
    end = adm["discharge_date"] or date.today()
    return max((end - adm["admission_date"]).days, 1)


def admissions_df():
    cols = ["admission_id", "patient_id", "patient_name", "ward", "bed", "admission_date",
            "discharge_date", "doctor_id", "doctor_name", "reason", "status", "length_of_stay"]
    data = [dict(a, patient_name=patient_name(a["patient_id"]), doctor_name=doctor_name(a["doctor_id"]),
                 length_of_stay=length_of_stay(a)) for a in S.admissions]
    df = pd.DataFrame(data, columns=cols)
    return df.sort_values("admission_date", ascending=False) if not df.empty else df


# ---------------------------------------------------------------------------
# Business rules
# ---------------------------------------------------------------------------
def recalc_invoice(inv, payments):
    """Recompute total, amount paid, balance and payment status for one invoice.
    Only payments with status 'Completed' count as money received."""
    inv["total"] = round(inv["consultation"] + inv["medicine"] + inv["lab"] + inv["other"], 2)
    paid = sum(p["amount"] for p in payments
               if p["invoice_id"] == inv["invoice_id"] and p["status"] == "Completed")
    inv["amount_paid"] = round(paid, 2)
    inv["balance"] = round(inv["total"] - paid, 2)
    if inv["balance"] <= 0:
        inv["payment_status"] = "Paid"
    elif paid > 0:
        inv["payment_status"] = "Partially Paid"
    else:
        inv["payment_status"] = "Unpaid"


def slot_conflict(doctor_id, day, slot, ignore_id=None):
    """Return the appointment that blocks this doctor/date/time, or None.
    All appointments last SLOT_MINUTES, so a conflict = same doctor, date and slot.
    Cancelled and No Show appointments do not block a slot."""
    for a in S.appointments:
        if (a["doctor_id"] == doctor_id and a["date"] == day and a["time"] == slot
                and a["status"] not in FREE_SLOT_STATUSES and a["appointment_id"] != ignore_id):
            return a
    return None


def is_in_past(day, slot):
    now = datetime.now()
    if day < now.date():
        return True
    return day == now.date() and slot < now.strftime("%H:%M")


def patient_in_use(pid):
    return any(r["patient_id"] == pid for r in S.appointments + S.invoices + S.payments + S.admissions)


def doctor_in_use(did):
    return any(r["doctor_id"] == did for r in S.appointments + S.admissions)


def active_admission(pid):
    for a in S.admissions:
        if a["patient_id"] == pid and a["status"] == "Admitted":
            return a
    return None


def bed_taken(bed, ignore_id=None):
    return any(a["bed"] == bed and a["status"] == "Admitted" and a["admission_id"] != ignore_id
               for a in S.admissions)


# ---------------------------------------------------------------------------
# Sample data (fictional) - built once per session
# ---------------------------------------------------------------------------
def build_sample_data():
    rnd = random.Random(2026)  # fixed seed -> consistent sample data
    today = date.today()

    def phone():
        return f"+1-555-{rnd.randint(100, 999)}-{rnd.randint(1000, 9999)}"

    # ---- Patients (first 12 registered 60-150 days ago, the rest more recently)
    seeds = [
        ("Ayesha Rahman", "Female", "O+"), ("Bilal Hussain", "Male", "B+"),
        ("Chloe Martin", "Female", "A+"), ("Daniel Okafor", "Male", "AB+"),
        ("Elena Petrova", "Female", "O-"), ("Farhan Siddiqui", "Male", "A-"),
        ("Grace Thompson", "Female", "B-"), ("Hamza Yusuf", "Male", "O+"),
        ("Isabel Costa", "Female", "A+"), ("Jamal Carter", "Male", "B+"),
        ("Kiran Patel", "Female", "AB-"), ("Liam Murphy", "Male", "O+"),
        ("Maryam Nasser", "Female", "A+"), ("Noah Bennett", "Male", "O-"),
        ("Olivia Chen", "Female", "B+"), ("Pedro Alvarez", "Male", "A+"),
        ("Qasim Raza", "Male", "AB+"), ("Rania Haddad", "Female", "O+"),
        ("Samuel Green", "Male", "B-"), ("Tahira Begum", "Female", "A+"),
    ]
    relatives = ["Amir", "Sofia", "Karim", "Lena", "Omar", "Nora", "Yusuf", "Mia"]
    patients = []
    for i, (name, gender, blood) in enumerate(seeds):
        first, last = name.split()
        age = rnd.randint(3, 85)
        days_ago = rnd.randint(60, 150) if i < 12 else rnd.randint(1, 59)
        patients.append({
            "patient_id": f"PAT-{i + 1:04d}", "name": name,
            "dob": today - timedelta(days=age * 365 + rnd.randint(0, 364)),
            "gender": gender, "phone": phone(),
            "email": f"{first.lower()}.{last.lower()}@example.com",
            "address": f"{rnd.randint(10, 99)} Sample Street, Fictionville",
            "blood_group": blood,
            "emergency_contact": f"{rnd.choice(relatives)} {last}", "emergency_phone": phone(),
            "registration_date": today - timedelta(days=days_ago),
            "status": "Inactive" if i in (5, 17) else "Active",
        })

    # ---- Doctors
    doc_seeds = [
        ("Dr. Sara Malik", "Cardiology", "Cardiology", 90, 12, "Available", "Full-time"),
        ("Dr. Imran Qureshi", "Neurology", "Neurology", 100, 15, "Available", "Full-time"),
        ("Dr. Hina Siddiqui", "Pediatrics", "Pediatrics", 60, 8, "Busy", "Full-time"),
        ("Dr. Usman Farooq", "Orthopedics", "Orthopedics", 85, 10, "Available", "Full-time"),
        ("Dr. Nadia Rauf", "Dermatology", "Dermatology", 70, 6, "Available", "Part-time"),
        ("Dr. Kamran Ali", "General Medicine", "General Medicine", 45, 9, "Available", "Full-time"),
        ("Dr. Farah Zaman", "Gynecology", "Obstetrics & Gynecology", 80, 14, "Available", "Full-time"),
        ("Dr. Tariq Mehmood", "General Surgery", "Surgery", 110, 18, "Available", "Visiting"),
        ("Dr. Zainab Hashmi", "Ophthalmology", "Ophthalmology", 75, 7, "On Leave", "Full-time"),
    ]
    doctors = []
    for i, (name, spec, dept, fee, years, avail, emp) in enumerate(doc_seeds):
        slug = name.replace("Dr. ", "").lower().replace(" ", ".")
        doctors.append({
            "doctor_id": f"DOC-{i + 1:04d}", "name": name, "specialization": spec,
            "department": dept, "phone": phone(), "email": f"dr.{slug}@example.com",
            "consultation_fee": float(fee), "availability": avail,
            "experience_years": years, "employment_status": emp,
        })

    # ---- Staff
    staff_seeds = [
        ("Maria Lopez", "Head Nurse", "Nursing", 3200, "Active"),
        ("James Wilson", "Nurse", "Nursing", 2600, "Active"),
        ("Fatima Noor", "Nurse", "Nursing", 2600, "On Leave"),
        ("Ethan Brooks", "Receptionist", "Administration", 1800, "Active"),
        ("Zoya Anwar", "Lab Technician", "Laboratory", 2400, "Active"),
        ("Victor Hugo", "Pharmacist", "Pharmacy", 3000, "Active"),
        ("Leila Karimi", "Radiographer", "Radiology", 2900, "Active"),
        ("Oscar Reed", "Accountant", "Finance", 3100, "Active"),
        ("Amina Sheikh", "Hospital Administrator", "Administration", 4200, "Active"),
        ("Ravi Menon", "Ward Attendant", "Support Services", 1500, "Active"),
        ("Hannah Fox", "Receptionist", "Administration", 1800, "Inactive"),
        ("Tomas Berg", "Security Guard", "Support Services", 1400, "Active"),
    ]
    staff = []
    for i, (name, title, dept, salary, status) in enumerate(staff_seeds):
        first, last = name.split()
        staff.append({
            "staff_id": f"STF-{i + 1:04d}", "name": name, "job_title": title, "department": dept,
            "phone": phone(), "email": f"{first.lower()}.{last.lower()}@example.com",
            "monthly_salary": float(salary),
            "joining_date": today - timedelta(days=rnd.randint(120, 3000)), "status": status,
        })

    # ---- Appointments (no doctor/time conflicts, patients exist and are registered by then)
    bookable = [d for d in doctors if d["availability"] != "On Leave" and d["employment_status"] != "Inactive"]
    active_patients = [p for p in patients if p["status"] == "Active"]
    appointments, taken = [], set()
    reasons = ["Routine check-up", "Chest pain evaluation", "Headache and dizziness", "Skin rash",
               "Back pain", "Fever and cough", "Follow-up visit", "Vaccination advice"]
    for offset in range(-40, 11):
        day = today + timedelta(days=offset)
        count = 6 if offset == 0 else rnd.randint(0, 2)
        for _ in range(count):
            doc = rnd.choice(bookable)
            pool = [p for p in active_patients if p["registration_date"] <= day]
            if not pool:
                continue
            patient = rnd.choice(pool)
            slot = rnd.choice(TIME_SLOTS)
            if (doc["doctor_id"], day, slot) in taken:
                continue
            taken.add((doc["doctor_id"], day, slot))
            if offset < 0:
                status = rnd.choices(["Completed", "Cancelled", "No Show"], [75, 13, 12])[0]
            elif offset == 0:
                status = rnd.choice(["Completed", "Completed", "In Progress", "Confirmed", "Scheduled", "Cancelled"])
            else:
                status = rnd.choice(["Scheduled", "Confirmed"])
            appointments.append({
                "appointment_id": f"APT-{len(appointments) + 1:04d}",
                "patient_id": patient["patient_id"], "doctor_id": doc["doctor_id"],
                "date": day, "time": slot, "type": rnd.choice(APPT_TYPES),
                "fee": doc["consultation_fee"], "status": status,
                "reason": rnd.choice(reasons), "notes": "",
            })

    # ---- Admissions (older patients only, unique active beds)
    adm_specs = [
        (0, "General Ward", "GW-101", 5, "Pneumonia observation", 3, None),
        (1, "ICU", "ICU-02", 0, "Cardiac monitoring", 5, None),
        (2, "Pediatrics", "PED-05", 2, "Dehydration treatment", 2, None),
        (3, "Surgical", "SUR-03", 7, "Post-operative recovery", 1, None),
        (4, "General Ward", "GW-102", 5, "Viral fever", 30, 4),
        (6, "Maternity", "MAT-01", 6, "Childbirth", 22, 3),
        (7, "Surgical", "SUR-01", 3, "Fracture surgery", 15, 6),
    ]
    admissions = []
    for n, (pi, ward, bed, di, reason, days_ago, los) in enumerate(adm_specs, start=1):
        admitted = today - timedelta(days=days_ago)
        admissions.append({
            "admission_id": f"ADM-{n:04d}", "patient_id": patients[pi]["patient_id"],
            "ward": ward, "bed": bed, "admission_date": admitted,
            "discharge_date": admitted + timedelta(days=los) if los else None,
            "doctor_id": doctors[di]["doctor_id"], "reason": reason,
            "status": "Discharged" if los else "Admitted",
        })

    # ---- Invoices and payments
    invoices, payments = [], []

    def make_invoice(patient_id, appt_id, bdate, consult, medicine, lab, other):
        inv = {"invoice_id": f"INV-{len(invoices) + 1:04d}", "patient_id": patient_id,
               "appointment_id": appt_id, "billing_date": bdate, "consultation": float(consult),
               "medicine": float(medicine), "lab": float(lab), "other": float(other),
               "total": 0.0, "amount_paid": 0.0, "balance": 0.0, "payment_status": "Unpaid"}
        invoices.append(inv)
        return inv

    def make_payment(inv, amount, method, status, pdate):
        reference = "" if method == "Cash" else f"TXN-{rnd.randint(100000, 999999)}"
        payments.append({
            "payment_id": f"PAY-{len(payments) + 1:04d}", "invoice_id": inv["invoice_id"],
            "patient_id": inv["patient_id"], "amount": round(amount, 2), "method": method,
            "payment_date": pdate, "status": status, "reference": reference,
        })

    for appt in appointments:
        if appt["status"] != "Completed" or rnd.random() < 0.1:
            continue  # a few completed visits stay un-invoiced for the demo
        inv = make_invoice(appt["patient_id"], appt["appointment_id"], appt["date"], appt["fee"],
                           rnd.choice([0, 15, 35, 60]), rnd.choice([0, 0, 25, 70, 120]),
                           rnd.choice([0, 0, 10, 20]))
        total = inv["consultation"] + inv["medicine"] + inv["lab"] + inv["other"]
        pdate = min(inv["billing_date"] + timedelta(days=rnd.randint(0, 3)), today)
        method = rnd.choice(PAYMENT_METHODS)
        roll = rnd.random()
        if roll < 0.60:
            make_payment(inv, total, method, "Completed", pdate)
        elif roll < 0.75:
            make_payment(inv, total / 2, method, "Completed", pdate)
        elif roll < 0.85:
            make_payment(inv, total, "Credit/Debit Card", "Failed", pdate)
            make_payment(inv, total, "Cash", "Completed", pdate)
        elif roll < 0.90:
            make_payment(inv, total, "Bank Transfer", "Pending", pdate)
        elif roll < 0.95:
            make_payment(inv, total, method, "Refunded", pdate)
        # else: no payment yet

    # Hospital-stay invoices for the discharged admissions (no appointment)
    for adm, payment_plan in zip([a for a in admissions if a["status"] == "Discharged"],
                                 ["full", "partial", "none"]):
        stay = (adm["discharge_date"] - adm["admission_date"]).days
        doc = find(doctors, "doctor_id", adm["doctor_id"])
        inv = make_invoice(adm["patient_id"], "", adm["discharge_date"], doc["consultation_fee"],
                           150, 90, 80 * stay)
        total = inv["consultation"] + inv["medicine"] + inv["lab"] + inv["other"]
        if payment_plan == "full":
            make_payment(inv, total, "Insurance", "Completed", adm["discharge_date"])
        elif payment_plan == "partial":
            make_payment(inv, total / 2, "Credit/Debit Card", "Completed", adm["discharge_date"])

    for inv in invoices:
        recalc_invoice(inv, payments)

    return {"patients": patients, "doctors": doctors, "staff": staff, "appointments": appointments,
            "admissions": admissions, "invoices": invoices, "payments": payments}


def init_state():
    """Load sample data only once per session so user changes survive reruns."""
    if "initialized" not in S:
        for key, value in build_sample_data().items():
            S[key] = value
        S["flash"] = []
        S["initialized"] = True


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def compute_kpis():
    today = date.today()
    appts = S.appointments
    return {
        "patients": len(S.patients), "doctors": len(S.doctors), "staff": len(S.staff),
        "appointments": len(appts),
        "today": sum(1 for a in appts if a["date"] == today),
        "completed": sum(1 for a in appts if a["status"] == "Completed"),
        "pending": sum(1 for a in appts if a["status"] in PENDING_APPT_STATUSES),
        "cancelled": sum(1 for a in appts if a["status"] == "Cancelled"),
        "revenue": sum(p["amount"] for p in S.payments if p["status"] == "Completed"),
        "outstanding": sum(i["balance"] for i in S.invoices),
        "admitted": sum(1 for a in S.admissions if a["status"] == "Admitted"),
    }


def draw_chart(fig, empty_message="Not enough data to draw this chart yet."):
    """Render a Plotly figure inside a bordered card (or a friendly message)."""
    with st.container(border=True):
        if fig is None:
            st.info(empty_message)
            return
        fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), title_font_color="#14407a")
        st.plotly_chart(fig, width="stretch")


def chart_registrations():
    df = patients_df()
    if df.empty:
        return None
    weeks = pd.to_datetime(df["registration_date"]).dt.to_period("W").dt.start_time
    data = weeks.value_counts().sort_index().rename_axis("Week starting").reset_index(name="Registrations")
    return px.bar(data, x="Week starting", y="Registrations", title="Patient registration trend (weekly)",
                  color_discrete_sequence=BLUES)


def chart_appointments_by_date():
    df = appointments_df()
    if df.empty:
        return None
    data = df.groupby("date").size().reset_index(name="Appointments")
    return px.bar(data, x="date", y="Appointments", title="Appointments by date",
                  labels={"date": "Date"}, color_discrete_sequence=BLUES)


def chart_status_distribution():
    df = appointments_df()
    if df.empty:
        return None
    data = df["status"].value_counts().rename_axis("Status").reset_index(name="Appointments")
    return px.pie(data, names="Status", values="Appointments", hole=0.45,
                  title="Appointment status distribution", color_discrete_sequence=BLUES)


def chart_revenue_trend():
    df = payments_df()
    df = df[df["status"] == "Completed"] if not df.empty else df
    if df.empty:
        return None
    data = df.groupby("payment_date")["amount"].sum().reset_index()
    data.columns = ["Date", "Revenue"]
    fig = px.line(data, x="Date", y="Revenue", markers=True, title=f"Revenue received by date ({CURRENCY})",
                  color_discrete_sequence=BLUES)
    return fig


def chart_payment_methods():
    df = payments_df()
    df = df[df["status"] == "Completed"] if not df.empty else df
    if df.empty:
        return None
    data = df.groupby("method")["amount"].sum().reset_index()
    data.columns = ["Method", "Amount"]
    return px.pie(data, names="Method", values="Amount", hole=0.45,
                  title="Payment-method distribution (completed payments)", color_discrete_sequence=BLUES)


def chart_doctor_appointments():
    df = appointments_df()
    if df.empty:
        return None
    data = df.groupby("doctor_name").size().reset_index(name="Appointments").sort_values("Appointments")
    return px.bar(data, x="Appointments", y="doctor_name", orientation="h",
                  title="Appointments per doctor", labels={"doctor_name": "Doctor"},
                  color_discrete_sequence=BLUES)


def chart_gender():
    df = patients_df()
    if df.empty:
        return None
    data = df["gender"].value_counts().rename_axis("Gender").reset_index(name="Patients")
    return px.pie(data, names="Gender", values="Patients", hole=0.45,
                  title="Patients by gender", color_discrete_sequence=BLUES)


def chart_inpatient_outpatient():
    outpatient = len(S.appointments)
    inpatient = len(S.admissions)
    if outpatient + inpatient == 0:
        return None
    data = pd.DataFrame({"Type": ["Outpatient visits (appointments)", "Inpatient admissions"],
                         "Count": [outpatient, inpatient]})
    return px.bar(data, x="Type", y="Count", title="Inpatient and outpatient statistics",
                  color="Type", color_discrete_sequence=BLUES)


def page_dashboard():
    st.title("🏥 Hospital Management Dashboard")
    st.info(STORAGE_NOTICE)
    k = compute_kpis()

    c = st.columns(4)
    c[0].metric("Total patients", k["patients"])
    c[1].metric("Total doctors", k["doctors"])
    c[2].metric("Total hospital staff", k["staff"])
    c[3].metric("Admitted patients", k["admitted"])
    c = st.columns(4)
    c[0].metric("Total appointments", k["appointments"])
    c[1].metric("Today's appointments", k["today"])
    c[2].metric("Completed appointments", k["completed"])
    c[3].metric("Pending appointments", k["pending"], help="Scheduled + Confirmed + In Progress")
    c = st.columns(4)
    c[0].metric("Cancelled appointments", k["cancelled"])
    c[1].metric("Total revenue received", money(k["revenue"]), help="Completed payments only")
    c[2].metric("Outstanding payments", money(k["outstanding"]), help="Unpaid balance on all invoices")

    st.subheader("📊 Analytics")
    left, right = st.columns(2)
    with left:
        draw_chart(chart_registrations())
        draw_chart(chart_status_distribution())
        draw_chart(chart_payment_methods())
        draw_chart(chart_gender())
    with right:
        draw_chart(chart_appointments_by_date())
        draw_chart(chart_revenue_trend())
        draw_chart(chart_doctor_appointments())
        draw_chart(chart_inpatient_outpatient())

    st.subheader("📅 Today's appointments")
    today = date.today()
    todays = [a for a in S.appointments if a["date"] == today]
    show_table(appointments_df(todays).sort_values("time") if todays else appointments_df([]),
               "No appointments today.")

    st.subheader("⏭️ Upcoming appointments (next 14 days)")
    upcoming = [a for a in S.appointments
                if today < a["date"] <= today + timedelta(days=14) and a["status"] in ("Scheduled", "Confirmed")]
    upcoming_df = appointments_df(upcoming)
    if not upcoming_df.empty:
        upcoming_df = upcoming_df.sort_values(["date", "time"])
    show_table(upcoming_df, "No upcoming appointments.")


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------
def validate_patient(name, phone, email, address, em_name, em_phone, dob):
    errors = []
    if not name.strip():
        errors.append("Full name is required.")
    errors += validate_contact(phone, email)
    if not address.strip():
        errors.append("Home address is required.")
    if not em_name.strip():
        errors.append("Emergency contact name is required.")
    if not valid_phone(em_phone):
        errors.append("Emergency contact phone number is invalid.")
    if dob > date.today():
        errors.append("Date of birth cannot be in the future.")
    return errors


def page_patients():
    st.header("🧑 Patients")
    tab_list, tab_add, tab_edit = st.tabs(["📋 Patient list", "➕ Register patient", "✏️ Edit / delete"])

    with tab_list:
        df = patients_df()
        c = st.columns([2, 1, 1, 1])
        query = c[0].text_input("Search (ID, name, phone, email)", key="pl_search")
        genders = c[1].multiselect("Gender", GENDERS, key="pl_gender")
        bloods = c[2].multiselect("Blood group", BLOOD_GROUPS, key="pl_blood")
        statuses = c[3].multiselect("Status", PATIENT_STATUSES, key="pl_status")
        df = text_search(df, query, ["patient_id", "name", "phone", "email"])
        df = pick(pick(pick(df, "gender", genders), "blood_group", bloods), "status", statuses)
        st.caption(f"Showing {len(df)} of {len(S.patients)} patients. Click a column header to sort.")
        show_table(df, "No patients match your filters.")

    with tab_add:
        st.subheader("Register a new patient")
        with st.form("add_patient"):
            c1, c2 = st.columns(2)
            pid_in = c1.text_input("Patient ID (optional, e.g. PAT-0100)", key="pa_id",
                                   help="Leave blank to generate automatically.")
            name = c2.text_input("Full name *", key="pa_name")
            dob = c1.date_input("Date of birth *", value=date(1990, 1, 1), min_value=date(1900, 1, 1),
                                max_value=date.today(), key="pa_dob")
            gender = c2.selectbox("Gender *", GENDERS, key="pa_gender")
            phone = c1.text_input("Phone number *", placeholder="+1-555-123-4567", key="pa_phone")
            email = c2.text_input("Email address *", placeholder="name@example.com", key="pa_email")
            blood = c1.selectbox("Blood group *", BLOOD_GROUPS, key="pa_blood")
            status = c2.selectbox("Patient status", PATIENT_STATUSES, key="pa_status")
            address = st.text_area("Home address *", key="pa_address")
            c3, c4, c5 = st.columns(3)
            em_name = c3.text_input("Emergency contact name *", key="pa_emname")
            em_phone = c4.text_input("Emergency contact phone *", key="pa_emphone")
            reg_date = c5.date_input("Registration date", value=date.today(), max_value=date.today(),
                                     key="pa_reg")
            submitted = st.form_submit_button("Register patient", type="primary")
        if submitted:
            errors = validate_patient(name, phone, email, address, em_name, em_phone, dob)
            new_id, id_error = resolve_id(pid_in, "PAT", [p["patient_id"] for p in S.patients])
            if id_error:
                errors.append(id_error)
            if errors:
                show_errors(errors)
            else:
                S.patients.append({
                    "patient_id": new_id, "name": name.strip(), "dob": dob, "gender": gender,
                    "phone": phone.strip(), "email": email.strip(), "address": address.strip(),
                    "blood_group": blood, "emergency_contact": em_name.strip(),
                    "emergency_phone": em_phone.strip(), "registration_date": reg_date, "status": status,
                })
                flash("success", f"Patient {name.strip()} registered with ID {new_id}.")
                clear_keys("pa_")
                st.rerun()

    with tab_edit:
        if not S.patients:
            st.info("No patients to edit.")
            return
        labels = patient_labels()
        pid = st.selectbox("Select patient", list(labels), format_func=labels.get, key="pe_select")
        p = find(S.patients, "patient_id", pid)
        with st.form(f"edit_patient_{pid}"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full name *", value=p["name"], key=f"pe_name_{pid}")
            dob = c2.date_input("Date of birth *", value=p["dob"], min_value=date(1900, 1, 1),
                                max_value=date.today(), key=f"pe_dob_{pid}")
            gender = c1.selectbox("Gender *", GENDERS, index=GENDERS.index(p["gender"]), key=f"pe_gender_{pid}")
            blood = c2.selectbox("Blood group *", BLOOD_GROUPS, index=BLOOD_GROUPS.index(p["blood_group"]),
                                 key=f"pe_blood_{pid}")
            phone = c1.text_input("Phone number *", value=p["phone"], key=f"pe_phone_{pid}")
            email = c2.text_input("Email address *", value=p["email"], key=f"pe_email_{pid}")
            status = c1.selectbox("Status", PATIENT_STATUSES, index=PATIENT_STATUSES.index(p["status"]),
                                  key=f"pe_status_{pid}")
            address = st.text_area("Home address *", value=p["address"], key=f"pe_address_{pid}")
            c3, c4 = st.columns(2)
            em_name = c3.text_input("Emergency contact name *", value=p["emergency_contact"], key=f"pe_emn_{pid}")
            em_phone = c4.text_input("Emergency contact phone *", value=p["emergency_phone"], key=f"pe_emp_{pid}")
            saved = st.form_submit_button("Save changes", type="primary")
        if saved:
            errors = validate_patient(name, phone, email, address, em_name, em_phone, dob)
            if errors:
                show_errors(errors)
            else:
                p.update(name=name.strip(), dob=dob, gender=gender, blood_group=blood, phone=phone.strip(),
                         email=email.strip(), status=status, address=address.strip(),
                         emergency_contact=em_name.strip(), emergency_phone=em_phone.strip())
                flash("success", f"Patient {pid} updated.")
                st.rerun()

        with st.expander("🗑️ Delete this patient"):
            if patient_in_use(pid):
                st.warning("This patient has appointments, invoices, payments or admissions, so the record "
                           "cannot be deleted. Set the status to **Inactive** instead.")
            else:
                st.warning(f"You are about to permanently delete {p['name']} ({pid}).")
                if confirm_delete(f"del_pat_{pid}", "Yes, I understand this cannot be undone"):
                    S.patients.remove(p)
                    flash("success", f"Patient {pid} deleted.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Doctors
# ---------------------------------------------------------------------------
def validate_doctor(name, specialization, department, phone, email, fee):
    errors = []
    if not name.strip():
        errors.append("Doctor name is required.")
    if not specialization.strip():
        errors.append("Specialization is required.")
    if not department.strip():
        errors.append("Department is required.")
    errors += validate_contact(phone, email)
    if fee <= 0:
        errors.append("Consultation fee must be greater than zero.")
    return errors


def page_doctors():
    st.header("🩺 Doctors")
    tab_list, tab_add, tab_edit = st.tabs(["📋 Doctor list", "➕ Add doctor", "✏️ Edit / delete"])

    with tab_list:
        df = doctors_df()
        c = st.columns([2, 1, 1, 1])
        query = c[0].text_input("Search (name or ID)", key="dl_search")
        specs = c[1].multiselect("Specialization", sorted(df["specialization"].unique()), key="dl_spec")
        depts = c[2].multiselect("Department", sorted(df["department"].unique()), key="dl_dept")
        avail = c[3].multiselect("Availability", AVAILABILITY, key="dl_avail")
        df = text_search(df, query, ["doctor_id", "name"])
        df = pick(pick(pick(df, "specialization", specs), "department", depts), "availability", avail)
        st.caption(f"Showing {len(df)} of {len(S.doctors)} doctors.")
        show_table(df, "No doctors match your filters.")

    with tab_add:
        st.subheader("Add a new doctor")
        with st.form("add_doctor"):
            c1, c2 = st.columns(2)
            did_in = c1.text_input("Doctor ID (optional, e.g. DOC-0100)", key="da_id",
                                   help="Leave blank to generate automatically.")
            name = c2.text_input("Full name *", placeholder="Dr. Jane Doe", key="da_name")
            spec = c1.text_input("Specialization *", key="da_spec")
            dept = c2.text_input("Department *", key="da_dept")
            phone = c1.text_input("Phone number *", placeholder="+1-555-123-4567", key="da_phone")
            email = c2.text_input("Email address *", placeholder="name@example.com", key="da_email")
            fee = c1.number_input(f"Consultation fee ({CURRENCY}) *", min_value=0.0, max_value=100000.0,
                                  value=50.0, step=5.0, key="da_fee")
            years = c2.number_input("Years of experience", min_value=0, max_value=60, value=5, key="da_years")
            avail = c1.selectbox("Availability", AVAILABILITY, key="da_avail")
            emp = c2.selectbox("Employment status", DOCTOR_EMPLOYMENT, key="da_emp")
            submitted = st.form_submit_button("Add doctor", type="primary")
        if submitted:
            errors = validate_doctor(name, spec, dept, phone, email, fee)
            new_id, id_error = resolve_id(did_in, "DOC", [d["doctor_id"] for d in S.doctors])
            if id_error:
                errors.append(id_error)
            if errors:
                show_errors(errors)
            else:
                S.doctors.append({
                    "doctor_id": new_id, "name": name.strip(), "specialization": spec.strip(),
                    "department": dept.strip(), "phone": phone.strip(), "email": email.strip(),
                    "consultation_fee": float(fee), "availability": avail,
                    "experience_years": int(years), "employment_status": emp,
                })
                flash("success", f"Doctor {name.strip()} added with ID {new_id}.")
                clear_keys("da_")
                st.rerun()

    with tab_edit:
        if not S.doctors:
            st.info("No doctors to edit.")
            return
        labels = doctor_labels()
        did = st.selectbox("Select doctor", list(labels), format_func=labels.get, key="de_select")
        d = find(S.doctors, "doctor_id", did)
        with st.form(f"edit_doctor_{did}"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full name *", value=d["name"], key=f"de_name_{did}")
            spec = c2.text_input("Specialization *", value=d["specialization"], key=f"de_spec_{did}")
            dept = c1.text_input("Department *", value=d["department"], key=f"de_dept_{did}")
            phone = c2.text_input("Phone number *", value=d["phone"], key=f"de_phone_{did}")
            email = c1.text_input("Email address *", value=d["email"], key=f"de_email_{did}")
            fee = c2.number_input(f"Consultation fee ({CURRENCY}) *", min_value=0.0, max_value=100000.0,
                                  value=float(d["consultation_fee"]), step=5.0, key=f"de_fee_{did}")
            years = c1.number_input("Years of experience", min_value=0, max_value=60,
                                    value=int(d["experience_years"]), key=f"de_years_{did}")
            avail = c2.selectbox("Availability", AVAILABILITY, index=AVAILABILITY.index(d["availability"]),
                                 key=f"de_avail_{did}")
            emp = c1.selectbox("Employment status", DOCTOR_EMPLOYMENT,
                               index=DOCTOR_EMPLOYMENT.index(d["employment_status"]), key=f"de_emp_{did}")
            saved = st.form_submit_button("Save changes", type="primary")
        if saved:
            errors = validate_doctor(name, spec, dept, phone, email, fee)
            if errors:
                show_errors(errors)
            else:
                d.update(name=name.strip(), specialization=spec.strip(), department=dept.strip(),
                         phone=phone.strip(), email=email.strip(), consultation_fee=float(fee),
                         experience_years=int(years), availability=avail, employment_status=emp)
                flash("success", f"Doctor {did} updated. (Existing appointments keep their booked fee.)")
                st.rerun()

        with st.expander("🗑️ Delete this doctor"):
            if doctor_in_use(did):
                st.warning("This doctor has appointments or admissions, so the record cannot be deleted. "
                           "Set the employment status to **Inactive** instead.")
            else:
                st.warning(f"You are about to permanently delete {d['name']} ({did}).")
                if confirm_delete(f"del_doc_{did}", "Yes, I understand this cannot be undone"):
                    S.doctors.remove(d)
                    flash("success", f"Doctor {did} deleted.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------
def booked_slots(doctor_id, day, ignore_id=None):
    return sorted(a["time"] for a in S.appointments
                  if a["doctor_id"] == doctor_id and a["date"] == day
                  and a["status"] not in FREE_SLOT_STATUSES and a["appointment_id"] != ignore_id)


def appointment_has_invoice(appt_id):
    return any(i["appointment_id"] == appt_id for i in S.invoices)


def page_appointments():
    st.header("📅 Appointments")
    st.caption(f"Scheduling assumption: every appointment lasts {SLOT_MINUTES} minutes and starts on a "
               f"{SLOT_MINUTES}-minute slot between {TIME_SLOTS[0]} and {TIME_SLOTS[-1]}. A doctor can "
               "have only one active appointment per slot. Cancelled and No Show appointments free the slot.")
    tab_list, tab_book, tab_manage = st.tabs(["📋 Appointment list", "➕ Book appointment", "🛠️ Manage"])

    with tab_list:
        today = date.today()
        df = appointments_df()
        c = st.columns([2, 2])
        query = c[0].text_input("Search (ID, patient, doctor)", key="al_search")
        statuses = c[1].multiselect("Status", APPT_STATUSES, key="al_status")
        start, end = date_range_inputs("al", today - timedelta(days=30), today + timedelta(days=30))
        if start is not None:
            df = filter_dates(df, "date", start, end)
            df = text_search(df, query, ["appointment_id", "patient_id", "patient_name", "doctor_id", "doctor_name"])
            df = pick(df, "status", statuses)
            st.caption(f"Showing {len(df)} appointments.")
            show_table(df, "No appointments match your filters.")

    with tab_book:
        st.subheader("Book a new appointment")
        patients = [p for p in S.patients if p["status"] == "Active"]
        doctors = [d for d in S.doctors if d["employment_status"] != "Inactive"]
        if not patients or not doctors:
            st.warning("You need at least one active patient and one non-inactive doctor to book appointments.")
        else:
            p_labels, d_labels = patient_labels(), doctor_labels()
            c1, c2 = st.columns(2)
            pid = c1.selectbox("Patient *", [p["patient_id"] for p in patients], format_func=p_labels.get,
                               key="ap_patient")
            did = c2.selectbox("Doctor *", [d["doctor_id"] for d in doctors], format_func=d_labels.get,
                               key="ap_doctor")
            doctor = find(S.doctors, "doctor_id", did)
            c1, c2, c3 = st.columns(3)
            allow_past = c3.checkbox("Allow past date (historical record)", key="ap_past")
            day = c1.date_input("Appointment date *", value=date.today(),
                                min_value=date(2000, 1, 1) if allow_past else date.today(), key="ap_date")
            slot = c2.selectbox("Time slot *", TIME_SLOTS, key="ap_time")
            c1, c2 = st.columns(2)
            a_type = c1.selectbox("Appointment type *", APPT_TYPES, key="ap_type")
            status_options = APPT_STATUSES if allow_past else ["Scheduled", "Confirmed"]
            status = c2.selectbox("Status", status_options, key="ap_status")
            reason = st.text_input("Reason for visit *", key="ap_reason")
            notes = st.text_area("Additional notes", key="ap_notes")
            st.info(f"💵 Consultation fee (auto): **{money(doctor['consultation_fee'])}**  |  "
                    f"Doctor availability: **{doctor['availability']}**")
            taken = booked_slots(did, day)
            st.caption("Already booked for this doctor on that date: " + (", ".join(taken) if taken else "none"))

            if st.button("Book appointment", type="primary", key="ap_submit"):
                errors = []
                if not reason.strip():
                    errors.append("Reason for visit is required.")
                if doctor["availability"] == "On Leave":
                    errors.append(f"{doctor['name']} is currently on leave and cannot take appointments.")
                if not allow_past and is_in_past(day, slot):
                    errors.append("The appointment is in the past. Tick 'Allow past date' for historical records.")
                clash = slot_conflict(did, day, slot)
                if clash:
                    errors.append(f"{doctor['name']} already has appointment {clash['appointment_id']} at "
                                  f"{slot} on {day}. Choose another time slot.")
                if errors:
                    show_errors(errors)
                else:
                    new_id = next_id("APT", [a["appointment_id"] for a in S.appointments])
                    S.appointments.append({
                        "appointment_id": new_id, "patient_id": pid, "doctor_id": did, "date": day,
                        "time": slot, "type": a_type, "fee": float(doctor["consultation_fee"]),
                        "status": status, "reason": reason.strip(), "notes": notes.strip(),
                    })
                    flash("success", f"Appointment {new_id} booked for {day} at {slot}. "
                                     f"Fee: {money(doctor['consultation_fee'])}.")
                    clear_keys("ap_")
                    st.rerun()

    with tab_manage:
        if not S.appointments:
            st.info("There are no appointments to manage.")
            return
        labels = appointment_labels()
        aid = st.selectbox("Select appointment", list(labels), format_func=labels.get, key="am_select")
        appt = find(S.appointments, "appointment_id", aid)
        action = st.radio("Action", ["Reschedule", "Change status", "Cancel appointment", "Delete record"],
                          horizontal=True, key=f"am_action_{aid}")

        if action == "Reschedule":
            if appt["status"] not in ("Scheduled", "Confirmed"):
                st.warning("Only Scheduled or Confirmed appointments can be rescheduled.")
            else:
                c1, c2 = st.columns(2)
                new_day = c1.date_input("New date", value=max(appt["date"], date.today()),
                                        min_value=date.today(), key=f"am_day_{aid}")
                default_slot = TIME_SLOTS.index(appt["time"]) if appt["time"] in TIME_SLOTS else 0
                new_slot = c2.selectbox("New time slot", TIME_SLOTS, index=default_slot, key=f"am_slot_{aid}")
                if st.button("Reschedule", type="primary", key=f"am_resched_{aid}"):
                    clash = slot_conflict(appt["doctor_id"], new_day, new_slot, ignore_id=aid)
                    if is_in_past(new_day, new_slot):
                        st.error("The new date/time is in the past.")
                    elif clash:
                        st.error(f"That slot is already taken by appointment {clash['appointment_id']}.")
                    else:
                        appt["date"], appt["time"] = new_day, new_slot
                        flash("success", f"Appointment {aid} moved to {new_day} at {new_slot}.")
                        st.rerun()

        elif action == "Change status":
            new_status = st.selectbox("New status", APPT_STATUSES, index=APPT_STATUSES.index(appt["status"]),
                                      key=f"am_status_{aid}")
            if st.button("Update status", type="primary", key=f"am_setstatus_{aid}"):
                if new_status == appt["status"]:
                    st.warning("The appointment already has this status.")
                elif appointment_has_invoice(aid) and new_status != "Completed":
                    st.error("An invoice exists for this appointment, so it must stay Completed.")
                elif new_status not in FREE_SLOT_STATUSES and slot_conflict(
                        appt["doctor_id"], appt["date"], appt["time"], ignore_id=aid):
                    st.error("Another active appointment now uses this slot, so this status cannot be restored.")
                else:
                    appt["status"] = new_status
                    flash("success", f"Appointment {aid} is now {new_status}.")
                    st.rerun()

        elif action == "Cancel appointment":
            if appt["status"] in ("Completed", "Cancelled", "No Show"):
                st.warning(f"A {appt['status']} appointment cannot be cancelled.")
            else:
                confirmed = st.checkbox("Yes, cancel this appointment", key=f"am_cancel_chk_{aid}")
                if st.button("Cancel appointment", type="primary", disabled=not confirmed,
                             key=f"am_cancel_{aid}"):
                    appt["status"] = "Cancelled"
                    flash("success", f"Appointment {aid} cancelled.")
                    st.rerun()

        else:  # Delete record
            if appointment_has_invoice(aid):
                st.warning("An invoice references this appointment, so it cannot be deleted.")
            elif confirm_delete(f"del_apt_{aid}", "Yes, permanently delete this appointment record"):
                S.appointments.remove(appt)
                flash("success", f"Appointment {aid} deleted.")
                st.rerun()


# ---------------------------------------------------------------------------
# Billing and payments
# ---------------------------------------------------------------------------
def page_billing():
    st.header("💳 Billing & Payments")
    st.warning("This is a **demonstration billing system**. It does not process real payments or store real "
               "financial data.")
    tabs = st.tabs(["🧾 Invoices", "➕ New invoice", "💵 Record payment", "📒 Payments", "🛠️ Manage invoices"])
    today = date.today()

    # ----- Invoice list
    with tabs[0]:
        df = invoices_df()
        c = st.columns([2, 1])
        query = c[0].text_input("Search (invoice, patient, appointment)", key="il_search")
        statuses = c[1].multiselect("Payment status", ["Unpaid", "Partially Paid", "Paid"], key="il_status")
        start, end = date_range_inputs("il", today - timedelta(days=120), today)
        if start is not None:
            df = filter_dates(df, "billing_date", start, end)
            df = text_search(df, query, ["invoice_id", "patient_id", "patient_name", "appointment_id"])
            df = pick(df, "payment_status", statuses)
            m = st.columns(3)
            m[0].metric("Invoices shown", len(df))
            m[1].metric("Total billed", money(df["total"].sum() if not df.empty else 0))
            m[2].metric("Outstanding", money(df["balance"].sum() if not df.empty else 0))
            show_table(df, "No invoices match your filters.")
            download_csv(df, "⬇️ Download invoices (CSV)", "invoices.csv", "dl_invoices")

    # ----- New invoice (plain widgets so totals update live)
    with tabs[1]:
        st.subheader("Create an invoice")
        if not S.patients:
            st.info("Register a patient first.")
        else:
            p_labels = patient_labels()
            pid = st.selectbox("Patient *", list(p_labels), format_func=p_labels.get, key="inv_patient")
            billed = {i["appointment_id"] for i in S.invoices}
            eligible = [a for a in S.appointments if a["patient_id"] == pid
                        and a["status"] == "Completed" and a["appointment_id"] not in billed]
            appt_options = [""] + [a["appointment_id"] for a in eligible]
            appt_label = {"": "No appointment (walk-in, lab or other service)"}
            appt_label.update({a["appointment_id"]: f"{a['appointment_id']} - {a['date']} with "
                               f"{doctor_name(a['doctor_id'])} ({money(a['fee'])})" for a in eligible})
            appt_id = st.selectbox("Related completed appointment (optional)", appt_options,
                                   format_func=appt_label.get, key=f"inv_appt_{pid}")
            default_fee = find(S.appointments, "appointment_id", appt_id)["fee"] if appt_id else 0.0
            c1, c2, c3, c4 = st.columns(4)
            consult = c1.number_input("Consultation charges", min_value=0.0, max_value=1_000_000.0,
                                      value=float(default_fee), step=5.0, key=f"inv_c_{pid}_{appt_id}")
            medicine = c2.number_input("Medicine charges", min_value=0.0, max_value=1_000_000.0, step=5.0,
                                       key="inv_m")
            lab = c3.number_input("Laboratory charges", min_value=0.0, max_value=1_000_000.0, step=5.0,
                                  key="inv_l")
            other = c4.number_input("Other charges", min_value=0.0, max_value=1_000_000.0, step=5.0,
                                    key="inv_o")
            c1, c2 = st.columns(2)
            bdate = c1.date_input("Billing date", value=today, max_value=today, key="inv_date")
            inv_in = c2.text_input("Invoice ID (optional, e.g. INV-0100)", key="inv_id")
            total = consult + medicine + lab + other
            st.metric("Invoice total (auto-calculated)", money(total))
            if st.button("Create invoice", type="primary", key="inv_submit"):
                errors = []
                if total <= 0:
                    errors.append("The invoice total must be greater than zero.")
                new_id, id_error = resolve_id(inv_in, "INV", [i["invoice_id"] for i in S.invoices])
                if id_error:
                    errors.append(id_error)
                if errors:
                    show_errors(errors)
                else:
                    inv = {"invoice_id": new_id, "patient_id": pid, "appointment_id": appt_id,
                           "billing_date": bdate, "consultation": float(consult), "medicine": float(medicine),
                           "lab": float(lab), "other": float(other), "total": 0.0, "amount_paid": 0.0,
                           "balance": 0.0, "payment_status": "Unpaid"}
                    recalc_invoice(inv, S.payments)
                    S.invoices.append(inv)
                    flash("success", f"Invoice {new_id} created for {money(inv['total'])}.")
                    clear_keys("inv_")
                    st.rerun()

    # ----- Record payment
    with tabs[2]:
        st.subheader("Record a payment")
        open_invoices = [i for i in S.invoices if i["balance"] > 0]
        if not open_invoices:
            st.success("All invoices are fully paid, or there are no invoices yet.")
        else:
            inv_labels = {i["invoice_id"]: f"{i['invoice_id']} | {patient_name(i['patient_id'])} | "
                          f"balance {money(i['balance'])}" for i in open_invoices}
            inv_id = st.selectbox("Invoice *", list(inv_labels), format_func=inv_labels.get, key="pay_invoice")
            inv = find(S.invoices, "invoice_id", inv_id)
            m = st.columns(3)
            m[0].metric("Invoice total", money(inv["total"]))
            m[1].metric("Already paid", money(inv["amount_paid"]))
            m[2].metric("Outstanding balance", money(inv["balance"]))
            c1, c2 = st.columns(2)
            amount = c1.number_input("Payment amount *", min_value=0.01, max_value=float(inv["balance"]),
                                     value=float(inv["balance"]), step=1.0,
                                     key=f"pay_amount_{inv_id}_{inv['balance']}")
            method = c2.selectbox("Payment method *", PAYMENT_METHODS, key="pay_method")
            pay_date = c1.date_input("Payment date", value=today, min_value=inv["billing_date"],
                                     max_value=today, key="pay_date")
            status = c2.selectbox("Payment status", ["Completed", "Pending", "Failed"], key="pay_status")
            reference = c1.text_input("Transaction reference (optional)", key="pay_ref")
            pay_in = c2.text_input("Payment ID (optional, e.g. PAY-0100)", key="pay_id")
            if st.button("Record payment", type="primary", key="pay_submit"):
                errors = []
                if amount <= 0:
                    errors.append("Payment amount must be greater than zero.")
                if amount > inv["balance"] + 0.001:
                    errors.append(f"Payment exceeds the outstanding balance of {money(inv['balance'])}.")
                new_id, id_error = resolve_id(pay_in, "PAY", [p["payment_id"] for p in S.payments])
                if id_error:
                    errors.append(id_error)
                if errors:
                    show_errors(errors)
                else:
                    S.payments.append({
                        "payment_id": new_id, "invoice_id": inv_id, "patient_id": inv["patient_id"],
                        "amount": round(float(amount), 2), "method": method, "payment_date": pay_date,
                        "status": status, "reference": reference.strip(),
                    })
                    recalc_invoice(inv, S.payments)
                    flash("success", f"Payment {new_id} ({status}) recorded. Invoice {inv_id} is now "
                                     f"{inv['payment_status']}.")
                    clear_keys("pay_")
                    st.rerun()

    # ----- Payment list and status updates
    with tabs[3]:
        df = payments_df()
        c = st.columns([2, 1, 1])
        query = c[0].text_input("Search (payment, invoice, patient, reference)", key="pl2_search")
        methods = c[1].multiselect("Method", PAYMENT_METHODS, key="pl2_method")
        statuses = c[2].multiselect("Status", PAYMENT_STATUSES, key="pl2_status")
        start, end = date_range_inputs("pl2", today - timedelta(days=120), today)
        if start is not None:
            df = filter_dates(df, "payment_date", start, end)
            df = text_search(df, query, ["payment_id", "invoice_id", "patient_id", "patient_name", "reference"])
            df = pick(pick(df, "method", methods), "status", statuses)
            received = df.loc[df["status"] == "Completed", "amount"].sum() if not df.empty else 0
            st.metric("Revenue received (completed payments in view)", money(received))
            show_table(df, "No payments match your filters.")
            download_csv(df, "⬇️ Download payments (CSV)", "payments.csv", "dl_payments")

            st.markdown("**Summary by method (completed payments)**")
            done = df[df["status"] == "Completed"] if not df.empty else df
            if done.empty:
                st.info("No completed payments in this view.")
            else:
                summary = done.groupby("method")["amount"].agg(["count", "sum"]).reset_index()
                summary.columns = ["method", "payments", "total_received"]
                show_table(summary)

        st.markdown("---")
        st.markdown("**Update a payment's status**")
        changeable = [p for p in S.payments if PAYMENT_TRANSITIONS[p["status"]]]
        if not changeable:
            st.info("No payments can be updated right now.")
        else:
            pay_labels = {p["payment_id"]: f"{p['payment_id']} | {p['invoice_id']} | {money(p['amount'])} | "
                          f"{p['status']}" for p in changeable}
            pid = st.selectbox("Payment", list(pay_labels), format_func=pay_labels.get, key="pu_select")
            pay = find(S.payments, "payment_id", pid)
            new_status = st.selectbox("New status", PAYMENT_TRANSITIONS[pay["status"]], key=f"pu_status_{pid}")
            if st.button("Update payment status", key=f"pu_btn_{pid}"):
                inv = find(S.invoices, "invoice_id", pay["invoice_id"])
                if new_status == "Completed" and pay["amount"] > inv["balance"] + 0.001:
                    st.error(f"Completing this payment would exceed the invoice balance ({money(inv['balance'])}).")
                else:
                    pay["status"] = new_status
                    recalc_invoice(inv, S.payments)
                    flash("success", f"Payment {pid} is now {new_status}. Invoice {inv['invoice_id']} "
                                     f"is {inv['payment_status']}.")
                    st.rerun()

        with st.expander("🗑️ Delete a payment record"):
            if not S.payments:
                st.info("No payments to delete.")
            else:
                all_labels = {p["payment_id"]: f"{p['payment_id']} | {p['invoice_id']} | {money(p['amount'])} | "
                              f"{p['status']}" for p in S.payments}
                del_id = st.selectbox("Payment to delete", list(all_labels), format_func=all_labels.get,
                                      key="pd_select")
                if confirm_delete(f"del_pay_{del_id}", "Yes, permanently delete this payment record"):
                    pay = find(S.payments, "payment_id", del_id)
                    S.payments.remove(pay)
                    recalc_invoice(find(S.invoices, "invoice_id", pay["invoice_id"]), S.payments)
                    flash("success", f"Payment {del_id} deleted and the invoice recalculated.")
                    st.rerun()

    # ----- Manage invoices (edit charges / delete)
    with tabs[4]:
        if not S.invoices:
            st.info("There are no invoices yet.")
        else:
            labels = {i["invoice_id"]: f"{i['invoice_id']} | {patient_name(i['patient_id'])} | "
                      f"total {money(i['total'])} | {i['payment_status']}" for i in S.invoices}
            iid = st.selectbox("Select invoice", list(labels), format_func=labels.get, key="im_select")
            inv = find(S.invoices, "invoice_id", iid)
            st.markdown("**Edit charges**")
            c = st.columns(4)
            consult = c[0].number_input("Consultation", min_value=0.0, max_value=1_000_000.0,
                                        value=float(inv["consultation"]), key=f"im_c_{iid}")
            medicine = c[1].number_input("Medicine", min_value=0.0, max_value=1_000_000.0,
                                         value=float(inv["medicine"]), key=f"im_m_{iid}")
            lab = c[2].number_input("Laboratory", min_value=0.0, max_value=1_000_000.0,
                                    value=float(inv["lab"]), key=f"im_l_{iid}")
            other = c[3].number_input("Other", min_value=0.0, max_value=1_000_000.0,
                                      value=float(inv["other"]), key=f"im_o_{iid}")
            new_total = consult + medicine + lab + other
            st.caption(f"New total: {money(new_total)} (already paid: {money(inv['amount_paid'])})")
            if st.button("Save charges", type="primary", key=f"im_save_{iid}"):
                if new_total <= 0:
                    st.error("The invoice total must be greater than zero.")
                elif new_total < inv["amount_paid"]:
                    st.error("The new total cannot be lower than the amount already paid.")
                else:
                    inv.update(consultation=float(consult), medicine=float(medicine), lab=float(lab),
                               other=float(other))
                    recalc_invoice(inv, S.payments)
                    flash("success", f"Invoice {iid} updated. Balance is now {money(inv['balance'])}.")
                    st.rerun()
            with st.expander("🗑️ Delete this invoice"):
                if any(p["invoice_id"] == iid for p in S.payments):
                    st.warning("This invoice has payment records. Delete those payments first.")
                elif confirm_delete(f"del_inv_{iid}", "Yes, permanently delete this invoice"):
                    S.invoices.remove(inv)
                    flash("success", f"Invoice {iid} deleted.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------
def validate_staff(name, title, dept, phone, email, salary):
    errors = []
    if not name.strip():
        errors.append("Full name is required.")
    if not title.strip():
        errors.append("Job title is required.")
    if not dept.strip():
        errors.append("Department is required.")
    errors += validate_contact(phone, email)
    if salary <= 0:
        errors.append("Monthly salary must be greater than zero.")
    return errors


def page_staff():
    st.header("👥 Hospital Staff")
    tab_list, tab_add, tab_edit = st.tabs(["📋 Staff list", "➕ Add staff member", "✏️ Edit / delete"])

    with tab_list:
        df = staff_df()
        c = st.columns([2, 1, 1, 1])
        query = c[0].text_input("Search (name or ID)", key="sl_search")
        depts = c[1].multiselect("Department", sorted(df["department"].unique()), key="sl_dept")
        titles = c[2].multiselect("Job title", sorted(df["job_title"].unique()), key="sl_title")
        statuses = c[3].multiselect("Employment status", STAFF_STATUSES, key="sl_status")
        df = text_search(df, query, ["staff_id", "name"])
        df = pick(pick(pick(df, "department", depts), "job_title", titles), "status", statuses)
        st.caption(f"Showing {len(df)} of {len(S.staff)} staff members.")
        show_table(df, "No staff members match your filters.")

    with tab_add:
        st.subheader("Add a staff member")
        with st.form("add_staff"):
            c1, c2 = st.columns(2)
            sid_in = c1.text_input("Staff ID (optional, e.g. STF-0100)", key="sa_id",
                                   help="Leave blank to generate automatically.")
            name = c2.text_input("Full name *", key="sa_name")
            title = c1.text_input("Job title *", key="sa_title")
            dept = c2.text_input("Department *", key="sa_dept")
            phone = c1.text_input("Phone number *", placeholder="+1-555-123-4567", key="sa_phone")
            email = c2.text_input("Email address *", placeholder="name@example.com", key="sa_email")
            salary = c1.number_input(f"Monthly salary ({CURRENCY}) *", min_value=0.0, max_value=1_000_000.0,
                                     value=2000.0, step=50.0, key="sa_salary")
            joined = c2.date_input("Joining date", value=date.today(), max_value=date.today(), key="sa_join")
            status = c1.selectbox("Employment status", STAFF_STATUSES, key="sa_status")
            submitted = st.form_submit_button("Add staff member", type="primary")
        if submitted:
            errors = validate_staff(name, title, dept, phone, email, salary)
            new_id, id_error = resolve_id(sid_in, "STF", [s["staff_id"] for s in S.staff])
            if id_error:
                errors.append(id_error)
            if errors:
                show_errors(errors)
            else:
                S.staff.append({
                    "staff_id": new_id, "name": name.strip(), "job_title": title.strip(),
                    "department": dept.strip(), "phone": phone.strip(), "email": email.strip(),
                    "monthly_salary": float(salary), "joining_date": joined, "status": status,
                })
                flash("success", f"Staff member {name.strip()} added with ID {new_id}.")
                clear_keys("sa_")
                st.rerun()

    with tab_edit:
        if not S.staff:
            st.info("No staff members to edit.")
            return
        labels = {s["staff_id"]: f"{s['staff_id']} - {s['name']} ({s['job_title']})" for s in S.staff}
        sid = st.selectbox("Select staff member", list(labels), format_func=labels.get, key="se_select")
        s = find(S.staff, "staff_id", sid)
        with st.form(f"edit_staff_{sid}"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full name *", value=s["name"], key=f"se_name_{sid}")
            title = c2.text_input("Job title *", value=s["job_title"], key=f"se_title_{sid}")
            dept = c1.text_input("Department *", value=s["department"], key=f"se_dept_{sid}")
            phone = c2.text_input("Phone number *", value=s["phone"], key=f"se_phone_{sid}")
            email = c1.text_input("Email address *", value=s["email"], key=f"se_email_{sid}")
            salary = c2.number_input(f"Monthly salary ({CURRENCY}) *", min_value=0.0, max_value=1_000_000.0,
                                     value=float(s["monthly_salary"]), step=50.0, key=f"se_salary_{sid}")
            joined = c1.date_input("Joining date", value=s["joining_date"], max_value=date.today(),
                                   key=f"se_join_{sid}")
            status = c2.selectbox("Employment status", STAFF_STATUSES, index=STAFF_STATUSES.index(s["status"]),
                                  key=f"se_status_{sid}")
            saved = st.form_submit_button("Save changes", type="primary")
        if saved:
            errors = validate_staff(name, title, dept, phone, email, salary)
            if errors:
                show_errors(errors)
            else:
                s.update(name=name.strip(), job_title=title.strip(), department=dept.strip(),
                         phone=phone.strip(), email=email.strip(), monthly_salary=float(salary),
                         joining_date=joined, status=status)
                flash("success", f"Staff member {sid} updated.")
                st.rerun()
        with st.expander("🗑️ Delete this staff member"):
            st.warning(f"You are about to permanently delete {s['name']} ({sid}).")
            if confirm_delete(f"del_stf_{sid}", "Yes, I understand this cannot be undone"):
                S.staff.remove(s)
                flash("success", f"Staff member {sid} deleted.")
                st.rerun()


# ---------------------------------------------------------------------------
# Admissions and discharges
# ---------------------------------------------------------------------------
def page_admissions():
    st.header("🛏️ Admissions & Discharges")
    st.caption("Bed numbers are unique across the hospital (for example GW-101). Length of stay counts "
               "calendar days; a same-day stay counts as 1 day.")
    tab_list, tab_admit, tab_discharge = st.tabs(["📋 Admissions", "➕ Admit patient", "🚪 Discharge / delete"])
    today = date.today()

    with tab_list:
        df = admissions_df()
        current = df[df["status"] == "Admitted"] if not df.empty else df
        st.subheader(f"Currently admitted ({len(current)})")
        show_table(current, "No patients are currently admitted.")
        st.subheader("All admission records")
        c = st.columns(2)
        wards = c[0].multiselect("Ward", WARDS, key="adl_ward")
        statuses = c[1].multiselect("Status", ADMISSION_STATUSES, key="adl_status")
        start, end = date_range_inputs("adl", today - timedelta(days=120), today)
        if start is not None:
            df = filter_dates(df, "admission_date", start, end)
            df = pick(pick(df, "ward", wards), "status", statuses)
            show_table(df, "No admissions match your filters.")

    with tab_admit:
        st.subheader("Admit a patient")
        candidates = [p for p in S.patients if p["status"] == "Active" and not active_admission(p["patient_id"])]
        doctors = [d for d in S.doctors if d["employment_status"] != "Inactive"]
        if not candidates or not doctors:
            st.warning("No eligible patients (active and not already admitted) or doctors available.")
        else:
            p_labels, d_labels = patient_labels(), doctor_labels()
            with st.form("admit_form"):
                c1, c2 = st.columns(2)
                pid = c1.selectbox("Patient *", [p["patient_id"] for p in candidates],
                                   format_func=p_labels.get, key="ad_patient")
                did = c2.selectbox("Attending doctor *", [d["doctor_id"] for d in doctors],
                                   format_func=d_labels.get, key="ad_doctor")
                ward = c1.selectbox("Ward / department *", WARDS, key="ad_ward")
                bed = c2.text_input("Bed number *", placeholder="e.g. GW-110", key="ad_bed")
                adm_date = c1.date_input("Admission date", value=today, max_value=today, key="ad_date")
                adm_in = c2.text_input("Admission ID (optional, e.g. ADM-0100)", key="ad_id")
                reason = st.text_input("Admission reason *", key="ad_reason")
                submitted = st.form_submit_button("Admit patient", type="primary")
            if submitted:
                errors = []
                bed_clean = bed.strip().upper()
                if not re.fullmatch(r"[A-Z0-9\-]{1,10}", bed_clean):
                    errors.append("Bed number is required (letters, digits and dashes, max 10 characters).")
                elif bed_taken(bed_clean):
                    errors.append(f"Bed {bed_clean} is already occupied by another admitted patient.")
                if not reason.strip():
                    errors.append("Admission reason is required.")
                if active_admission(pid):
                    errors.append("This patient already has an active admission.")
                new_id, id_error = resolve_id(adm_in, "ADM", [a["admission_id"] for a in S.admissions])
                if id_error:
                    errors.append(id_error)
                if errors:
                    show_errors(errors)
                else:
                    S.admissions.append({
                        "admission_id": new_id, "patient_id": pid, "ward": ward, "bed": bed_clean,
                        "admission_date": adm_date, "discharge_date": None, "doctor_id": did,
                        "reason": reason.strip(), "status": "Admitted",
                    })
                    flash("success", f"{patient_name(pid)} admitted to {ward}, bed {bed_clean} ({new_id}).")
                    clear_keys("ad_")
                    st.rerun()

    with tab_discharge:
        st.subheader("Discharge a patient")
        active = [a for a in S.admissions if a["status"] == "Admitted"]
        if not active:
            st.info("No patients are currently admitted.")
        else:
            labels = {a["admission_id"]: f"{a['admission_id']} | {patient_name(a['patient_id'])} | "
                      f"{a['ward']} bed {a['bed']} | since {a['admission_date']}" for a in active}
            aid = st.selectbox("Admission", list(labels), format_func=labels.get, key="dc_select")
            adm = find(S.admissions, "admission_id", aid)
            dc_date = st.date_input("Discharge date", value=max(today, adm["admission_date"]),
                                    min_value=adm["admission_date"], max_value=today, key=f"dc_date_{aid}")
            st.caption(f"Length of stay: {max((dc_date - adm['admission_date']).days, 1)} day(s)")
            if st.button("Discharge patient", type="primary", key=f"dc_btn_{aid}"):
                if dc_date < adm["admission_date"]:
                    st.error("Discharge date cannot be before the admission date.")
                else:
                    adm["discharge_date"], adm["status"] = dc_date, "Discharged"
                    flash("success", f"{patient_name(adm['patient_id'])} discharged. Bed {adm['bed']} is free.")
                    st.rerun()

        st.markdown("---")
        with st.expander("🗑️ Delete an admission record"):
            if not S.admissions:
                st.info("No admission records.")
            else:
                all_labels = {a["admission_id"]: f"{a['admission_id']} | {patient_name(a['patient_id'])} | "
                              f"{a['status']}" for a in S.admissions}
                del_id = st.selectbox("Admission record", list(all_labels), format_func=all_labels.get,
                                      key="adx_select")
                if confirm_delete(f"del_adm_{del_id}", "Yes, permanently delete this admission record"):
                    S.admissions.remove(find(S.admissions, "admission_id", del_id))
                    flash("success", f"Admission {del_id} deleted.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def page_reports():
    st.header("📑 Reports & CSV Downloads")
    today = date.today()
    start, end = date_range_inputs("rep", today - timedelta(days=90), today)
    if start is None:
        return
    st.caption(f"Reporting period: {start} to {end}")

    patients = filter_dates(patients_df(), "registration_date", start, end)
    appts = filter_dates(appointments_df(), "date", start, end)
    payments = filter_dates(payments_df(), "payment_date", start, end)
    received = payments[payments["status"] == "Completed"] if not payments.empty else payments
    invoices = filter_dates(invoices_df(), "billing_date", start, end)
    open_invoices = invoices[invoices["balance"] > 0] if not invoices.empty else invoices
    admissions_all = admissions_df()
    if admissions_all.empty:
        admissions = admissions_all
    else:
        in_adm = admissions_all["admission_date"].map(lambda d: start <= d <= end)
        in_dis = admissions_all["discharge_date"].map(lambda d: d is not None and start <= d <= end)
        admissions = admissions_all[(in_adm | in_dis).astype(bool)]
    staff = staff_df()
    staff = staff[staff["joining_date"].map(lambda d: d <= end).astype(bool)] if not staff.empty else staff

    completed_n = int((appts["status"] == "Completed").sum()) if not appts.empty else 0
    cancelled_n = int((appts["status"] == "Cancelled").sum()) if not appts.empty else 0
    c = st.columns(4)
    c[0].metric("New patients", len(patients))
    c[1].metric("Appointments", len(appts))
    c[2].metric("Completed", completed_n)
    c[3].metric("Cancelled", cancelled_n)
    c = st.columns(4)
    c[0].metric("Revenue received", money(received["amount"].sum() if not received.empty else 0))
    c[1].metric("Outstanding (invoices billed)", money(open_invoices["balance"].sum() if not open_invoices.empty else 0))
    c[2].metric("Admissions (in period)", int(admissions["admission_date"].map(lambda d: start <= d <= end).sum()) if not admissions.empty else 0)
    c[3].metric("Discharges (in period)", int(admissions["discharge_date"].map(lambda d: d is not None and start <= d <= end).sum()) if not admissions.empty else 0)

    tabs = st.tabs(["Patients", "Doctor appointments", "Completed & cancelled", "Revenue", "Outstanding",
                    "Payment methods", "Admissions", "Staff"])

    with tabs[0]:
        show_table(patients, "No patients registered in this period.")
        download_csv(patients, "⬇️ Download patient registrations", "patient_registrations.csv", "dl_r_pat")

    with tabs[1]:
        if appts.empty:
            st.info("No appointments in this period.")
            summary = pd.DataFrame(columns=["doctor_name", "total", "completed", "cancelled", "no_show"])
        else:
            summary = appts.groupby("doctor_name").agg(
                total=("appointment_id", "count"),
                completed=("status", lambda s: int((s == "Completed").sum())),
                cancelled=("status", lambda s: int((s == "Cancelled").sum())),
                no_show=("status", lambda s: int((s == "No Show").sum())),
            ).reset_index()
            show_table(summary)
        download_csv(summary, "⬇️ Download doctor summary", "doctor_appointments_summary.csv", "dl_r_doc")
        with st.expander("Appointment details"):
            show_table(appts)
        download_csv(appts, "⬇️ Download appointment details", "appointments_detail.csv", "dl_r_appt")

    with tabs[2]:
        subset = appts[appts["status"].isin(["Completed", "Cancelled"])] if not appts.empty else appts
        show_table(subset, "No completed or cancelled appointments in this period.")
        download_csv(subset, "⬇️ Download completed & cancelled", "completed_cancelled.csv", "dl_r_cc")

    with tabs[3]:
        if received.empty:
            st.info("No revenue received in this period.")
        else:
            by_date = received.groupby("payment_date")["amount"].sum().reset_index()
            by_date.columns = ["date", "revenue"]
            show_table(by_date)
            fig = px.bar(by_date, x="date", y="revenue", title="Revenue received by date",
                         color_discrete_sequence=BLUES)
            st.plotly_chart(fig, width="stretch")
        with st.expander("Payment details"):
            show_table(received)
        download_csv(received, "⬇️ Download revenue (payments)", "revenue_received.csv", "dl_r_rev")

    with tabs[4]:
        show_table(open_invoices, "No outstanding invoices for this period.")
        download_csv(open_invoices, "⬇️ Download outstanding invoices", "outstanding_invoices.csv", "dl_r_out")

    with tabs[5]:
        if received.empty:
            st.info("No completed payments in this period.")
            summary = pd.DataFrame(columns=["method", "payments", "total_received"])
        else:
            summary = received.groupby("method")["amount"].agg(["count", "sum"]).reset_index()
            summary.columns = ["method", "payments", "total_received"]
            show_table(summary)
        download_csv(summary, "⬇️ Download payment-method summary", "payment_methods.csv", "dl_r_pm")

    with tabs[6]:
        show_table(admissions, "No admissions or discharges in this period.")
        download_csv(admissions, "⬇️ Download admissions & discharges", "admissions.csv", "dl_r_adm")

    with tabs[7]:
        st.caption("Staff who had joined on or before the end date of the selected period.")
        show_table(staff, "No staff records for this period.")
        download_csv(staff, "⬇️ Download staff records", "staff_records.csv", "dl_r_staff")


# ---------------------------------------------------------------------------
# Main app: sidebar navigation
# ---------------------------------------------------------------------------
PAGES = {
    "🏠 Dashboard": page_dashboard,
    "🧑 Patients": page_patients,
    "🩺 Doctors": page_doctors,
    "📅 Appointments": page_appointments,
    "💳 Billing & Payments": page_billing,
    "👥 Hospital Staff": page_staff,
    "🛏️ Admissions": page_admissions,
    "📑 Reports": page_reports,
}


def main():
    init_state()
    inject_css()

    st.sidebar.title("🏥 Hospital Manager")
    page = st.sidebar.radio("Navigate", list(PAGES), key="nav")
    st.sidebar.warning("Demo with fictional data kept in temporary session memory. "
                       "Not for real patient or payment data.")
    with st.sidebar.expander("♻️ Reset demo data"):
        st.caption("Discard all changes and reload the original sample data.")
        confirmed = st.checkbox("Yes, reset everything", key="reset_chk")
        if st.button("Reset data", disabled=not confirmed, key="reset_btn"):
            for key, value in build_sample_data().items():
                S[key] = value
            S.flash = [("success", "Sample data has been reset.")]
            st.rerun()

    show_flash()
    PAGES[page]()


main()
