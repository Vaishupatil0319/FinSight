# FinSight – Personal Finance Intelligence

A Flask-based personal finance web application that helps users track income, manage expenses, analyze savings, set financial goals, and explore investment scenarios.

## Overview

FinSight provides a centralized dashboard for understanding personal finances. Users can create an account, record expenses, monitor their financial position, and explore illustrative investment plans based on their goals and risk preferences.

## Features

- **User Authentication:** Register, login, and logout.
- **Financial Profile:** Record monthly income, existing savings, and risk preference.
- **Expense Management:** Add and manage personal expenses.
- **Financial Dashboard:** View income, expenses, savings, saving rate, and financial health indicators.
- **Expense Analytics:** Analyze expenses by category and identify potential savings.
- **Financial Goals:** Set savings goals and estimate required monthly investments.
- **Balance Sheet:** View a summary of personal finances.
- **Smart Investment Planner:** Compare illustrative investment scenarios.
- **Data Visualization:** Interactive charts using Chart.js.
- **MySQL Database:** Store user profiles, expenses, and financial goals.

## Technology Stack

- **Backend:** Python, Flask
- **Database:** MySQL
- **Frontend:** HTML, CSS, Bootstrap
- **Charts:** Chart.js
- **Authentication:** Werkzeug password hashing
- **Templating:** Jinja2

## Project Structure

```text
Finsight/
├── app.py
├── database.py
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   ├── expenses.html
│   ├── dashboard.html
│   ├── analytics.html
│   ├── goals.html
│   ├── balance_sheet.html
│   └── investment_planner.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
└── README.md
```

*Adjust the file list to match your actual project folder.*

## Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Finsight
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure MySQL

- Create a MySQL database.
- Create the required tables for users, expenses, and financial goals.
- Configure the database connection in `database.py`.
- Ensure the `users` table supports the email and password hash fields required for authentication.

### 5. Configure the Flask secret key

Set a secure `FLASK_SECRET_KEY` environment variable before running the application. Do not commit real secrets or database passwords to GitHub.

### 6. Run the application

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Important Note

Investment returns shown in the planner are hypothetical estimates, not guaranteed returns or personalized financial advice. Actual returns depend on market conditions, product terms, fees, taxes, and investment risk.

## Future Improvements

- Monthly budget alerts
- Downloadable expense reports
- Improved financial report visualizations
- Additional automated financial insights

## Author

**Vaishnavi Vijay Patil**

MCA – Data Science

GitHub: [Vaishupatil0319](https://github.com/Vaishupatil0319)
