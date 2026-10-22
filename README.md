# hospital-management2
# 🏥 Hospital Management Dashboard

A beginner-friendly **Streamlit** web application for managing the day-to-day data of a small hospital: patients, doctors, appointments, billing and payments, hospital staff and inpatient admissions, with interactive charts and CSV reports.

> ⚠️ **This is a demonstration project.** All people, phone numbers and e-mail addresses are fictional. The billing module is **not** a real payment-processing service. Do **not** enter real patient, medical or financial data.

---

## Table of contents

1. [Main features](#main-features)
2. [Technologies used](#technologies-used)
3. [Project structure](#project-structure)
4. [Scheduling and billing assumptions](#scheduling-and-billing-assumptions)
5. [Prerequisites](#prerequisites)
6. [Run it on your computer](#run-it-on-your-computer)
7. [Create a GitHub repository and upload the files](#create-a-github-repository-and-upload-the-files)
8. [Deploy on Streamlit Community Cloud](#deploy-on-streamlit-community-cloud)
9. [Updating the app](#updating-the-app)
10. [Data-storage limitations](#data-storage-limitations)
11. [Privacy and security limitations](#privacy-and-security-limitations)
12. [Troubleshooting](#troubleshooting)
13. [Future improvements](#future-improvements)

---

## Main features

- **Dashboard** with 11 KPI cards (patients, doctors, staff, appointments, today's appointments, completed / pending / cancelled appointments, revenue received, outstanding payments, admitted patients), 8 interactive Plotly charts, and tables of today's and upcoming appointments.
- **Patients**: register, search, filter (gender, blood group, status), sort, edit and delete (with confirmation).
- **Doctors**: add, edit, search, filter (specialization, department, availability) and delete (with confirmation).
- **Appointments**: dropdown selection of patient and doctor, automatic consultation fee, conflict prevention, rescheduling, cancellation, status changes, date-range and status filters.
- **Billing & Payments**: invoices with automatic totals and balances, payment recording, payment-status updates, revenue by date and method, CSV downloads.
- **Hospital staff**: add, edit, search, filter and delete non-doctor employees.
- **Admissions & discharges**: admit and discharge patients, bed-conflict prevention, automatic length of stay, ward / status / date filters.
- **Reports**: date-range filtered reports with summary metrics and CSV downloads for eight report types.
- Input validation (required fields, phone numbers, e-mails, amounts, dates, IDs) and clear success / error messages.
- Realistic **fictional sample data** that is consistent (valid relationships, no scheduling or bed conflicts, invoice balances that match completed payments).

## Technologies used

| Library | Purpose |
|---|---|
| [Python 3.9+](https://www.python.org/) | Programming language |
| [Streamlit](https://streamlit.io/) | Web interface and session state |
| [Pandas](https://pandas.pydata.org/) | Tables, filtering, CSV generation |
| [Plotly](https://plotly.com/python/) | Interactive charts |

No database, paid service or external API is used.

## Project structure

```
hospital-dashboard/
├── app.py             # The entire application
├── requirements.txt   # Python libraries to install
└── README.md          # This documentation
```

## Scheduling and billing assumptions

**Appointments**

- Every appointment lasts exactly **30 minutes**.
- Clinic hours are **09:00 to 17:00**, so the 16 bookable start times run from 09:00 to 16:30.
- A doctor can have only **one active appointment per date and time slot**. Because every appointment has the same length, this also prevents overlaps.
- **Cancelled** and **No Show** appointments free their slot.
- New appointments cannot be booked in the past unless you tick *Allow past date (historical record)*.
- Doctors who are **On Leave** or whose employment status is **Inactive** cannot be booked.
- The consultation fee is copied from the doctor when the appointment is booked and is not changed if the doctor's fee is edited later.
- "Today" and "the current time" come from the computer running the app. On Streamlit Community Cloud that is usually UTC, so the time may differ from your local time.
- **Pending appointments** on the dashboard = Scheduled + Confirmed + In Progress.

**Billing**

- Invoice total = consultation + medicine + laboratory + other charges.
- Only payments with status **Completed** count as money received. Pending, Failed and Refunded payments do not.
- Outstanding balance = invoice total − completed payments.
- Invoice status: **Unpaid** (nothing received), **Partially Paid**, or **Paid** (balance is zero).
- A payment cannot exceed the invoice's outstanding balance. A payment's status can change from Pending to Completed or Failed, and from Completed to Refunded.
- The currency symbol is set by `CURRENCY` near the top of `app.py`.
- This is a demonstration system and does **not** process real payments.

**Admissions**

- A patient can have only one active admission, and a bed number can be used by only one admitted patient at a time.
- Length of stay counts calendar days; a same-day stay counts as 1 day.

## Prerequisites

- A laptop running Windows, macOS or Linux
- **Python 3.9 or newer** (3.11 or 3.12 recommended)
- A text editor (for example [VS Code](https://code.visualstudio.com/) or Notepad)
- A free [GitHub](https://github.com/) account (for deployment)
- A free [Streamlit Community Cloud](https://streamlit.io/cloud) account (for deployment)

### Installing Python

1. Go to <https://www.python.org/downloads/> and download the latest Python 3 installer.
2. **Windows:** run the installer and tick **"Add Python to PATH"** before clicking *Install Now*.
3. **macOS / Linux:** run the installer, or use your package manager (for example `brew install python`).
4. Check the installation by opening a terminal (Command Prompt / PowerShell on Windows, Terminal on macOS/Linux):

```bash
python --version
```

On macOS/Linux you may need `python3 --version` instead. You should see a version such as `Python 3.12.x`.

## Run it on your computer

### 1. Create the project folder and files

1. Create a folder named `hospital-dashboard` (for example on your Desktop).
2. Inside it, create three files named exactly `app.py`, `requirements.txt` and `README.md`.
3. Copy the provided contents into each file and save them.

### 2. Open a terminal in the folder

```bash
cd path/to/hospital-dashboard
```

(On Windows you can also open the folder, click the address bar, type `cmd` and press Enter.)

### 3. Create a virtual environment (recommended)

A virtual environment keeps this project's libraries separate from other Python projects.

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You should now see `(venv)` at the start of your terminal line.

> The `venv` folder is only for your computer. Do **not** upload it to GitHub.

### 4. Install the dependencies

```bash
pip install -r requirements.txt
```

### 5. Start the application

```bash
streamlit run app.py
```

Your browser opens automatically at <http://localhost:8501>. If not, copy that address into your browser. Press `Ctrl + C` in the terminal to stop the app.

## Create a GitHub repository and upload the files

### 1. Create the repository

1. Sign in at <https://github.com/>.
2. Click the **+** icon (top-right) → **New repository**.
3. Repository name: `hospital-dashboard`.
4. Choose **Public** (Streamlit Community Cloud's free tier works easily with public repositories).
5. Click **Create repository**.

### 2. Upload the three files (no command line needed)

1. On the new repository page click **uploading an existing file**.
2. Drag and drop `app.py`, `requirements.txt` and `README.md`.
3. Scroll down and click **Commit changes**.

### Alternative: upload with Git

```bash
git init
git add app.py requirements.txt README.md
git commit -m "Add hospital management dashboard"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/hospital-dashboard.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username.

## Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io/> and sign in with your GitHub account. Authorize access when asked.
2. Click **Create app** (or **New app**) and choose to deploy from an existing repository.
3. Select:
   - **Repository:** `YOUR-USERNAME/hospital-dashboard`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. (Optional) choose a custom app URL.
5. Click **Deploy**. The first build takes a few minutes while the libraries install.
6. When finished, your app is online at an address like `https://your-app-name.streamlit.app`. Share the link with anyone.

## Updating the app

1. Edit `app.py` (on your computer or directly on GitHub using the pencil ✏️ icon).
2. Commit the change to the `main` branch (upload the new file, or `git add`, `git commit`, `git push`).
3. Streamlit Community Cloud detects the commit and redeploys automatically. You can also open the app's menu and choose **Reboot app**.

If you change `requirements.txt`, the app reinstalls the libraries on the next deployment.

## Data-storage limitations

- All records live in **Streamlit session state**, which is memory for one browser session.
- Data is **temporary**. It is lost when you refresh or close the browser tab (a new session starts with fresh sample data), when the session times out, and whenever the deployed app restarts, sleeps or is redeployed.
- Different visitors each get their own separate copy of the data; changes are **not shared** between users.
- Use the CSV download buttons if you need to keep a copy of a report, and use the **Reset demo data** option in the sidebar to restore the original sample data.
- This app does **not** provide permanent storage.

## Privacy and security limitations

- The app has **no login, user accounts, roles or permissions**. Anyone with the link can use every feature.
- Data is not encrypted at rest and there is no audit log.
- The app is **not** designed or certified for HIPAA, GDPR or any other healthcare or privacy regulation.
- The billing module does not connect to any payment provider and must not be used for real transactions.
- Only enter fictional data. Do not store real patient, staff or financial information. Public GitHub repositories and public Streamlit apps are visible to everyone.

## Troubleshooting

| Problem | Solution |
|---|---|
| `streamlit: command not found` | Activate your virtual environment, or run `python -m streamlit run app.py` |
| `python: command not found` | Try `python3`, or reinstall Python and tick *Add Python to PATH* |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside your activated virtual environment |
| Deployment fails | Check that `app.py` and `requirements.txt` are in the **root** of the repository and the main file path is `app.py` |
| Data disappeared | Expected behaviour: session-state data is temporary (see above) |

## Future improvements

- Permanent storage with a free database (for example SQLite, or a hosted free-tier service)
- User login with roles (admin, doctor, receptionist) and an audit trail
- Doctor working schedules, variable appointment lengths and calendar views
- Printable invoices and appointment reminders by e-mail or SMS
- Electronic medical records: diagnoses, prescriptions, lab results
- Pharmacy and inventory management
- Insurance claim tracking and real payment-gateway integration
- Multi-language support, dark theme, and automated tests

## License

Provided for learning and demonstration purposes. Adapt it freely for your own projects.
