from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os
from functools import wraps
from database import get_db_connection
import csv
import io
from flask import send_file

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY",
    "replace-this-with-a-long-random-secret"
)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        requested_user_id = kwargs.get("user_id")

        if (
            requested_user_id is not None
            and requested_user_id != session["user_id"]
        ):
            return "Forbidden: You cannot access another user's data.", 403

        return view(*args, **kwargs)

    return wrapped_view


def calculate_monthly_investment(
    target_amount,
    current_amount,
    months,
    annual_return
):
    """
    Calculate approximate monthly investment
    required to reach a financial goal.

    Returns:
        monthly_investment
    """

    remaining_amount = max(
        target_amount - current_amount,
        0
    )

    if remaining_amount <= 0:
        return 0

    if months <= 0:
        return 0

    monthly_rate = annual_return / 100 / 12

    if monthly_rate == 0:

        return remaining_amount / months

    monthly_investment = (
        remaining_amount
        * monthly_rate
        / (
            (1 + monthly_rate) ** months
            - 1
        )
    )

    return monthly_investment

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Enter your name, valid email and password with at least 8 characters.", "danger")
            return render_template("register.html")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )

            if cursor.fetchone():
                flash("This email is already registered. Please log in.", "warning")
                return render_template("register.html")
            

            cursor.execute("""
                INSERT INTO users
                    (name, email, password_hash,
                     monthly_income, existing_savings, risk_preference)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                name,
                email,
                generate_password_hash(password),
                0,
                0,
                "Medium"
            ))

            connection.commit()
            user_id = cursor.lastrowid

            session.clear()
            session["user_id"] = user_id
            session.permanent = True

            return redirect(url_for("profile"))

        except Exception:
            connection.rollback()
            flash("Registration failed. Please try again.", "danger")
            return render_template("register.html")

        finally:
            cursor.close()
            connection.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT id, password_hash
                FROM users
                WHERE email = %s
            """, (email,))

            user = cursor.fetchone()

            if (
                user
                and user["password_hash"]
                and check_password_hash(user["password_hash"], password)
            ):
                session.clear()
                session["user_id"] = user["id"]
                session.permanent = True

                return redirect(
                    url_for("dashboard", user_id=user["id"])
                )

            flash("Invalid email or password.", "danger")

        finally:
            cursor.close()
            connection.close()

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("home"))


@app.route("/")
def home():
    return render_template("index.html")



@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            monthly_income = float(request.form.get("monthly_income", 0))
            existing_savings = float(request.form.get("existing_savings", 0))
            risk_preference = request.form.get("risk_preference", "Medium")

            if (
                not name
                or monthly_income < 0
                or existing_savings < 0
            ):
                flash("Please enter valid financial details.", "danger")
                return redirect(url_for("profile"))

            cursor.execute("""
                UPDATE users
                SET name = %s,
                    monthly_income = %s,
                    existing_savings = %s,
                    risk_preference = %s
                WHERE id = %s
            """, (
                name,
                monthly_income,
                existing_savings,
                risk_preference,
                user_id
            ))

            connection.commit()

            flash("Profile saved successfully!", "success")
            return redirect(url_for("expenses", user_id=user_id))

        cursor.execute(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        return render_template("profile.html", user=user)

    except (ValueError, TypeError):
        connection.rollback()
        flash("Please enter valid numbers for income and savings.", "danger")
        return redirect(url_for("profile"))

    except Exception:
        connection.rollback()
        flash("Unable to save your profile. Please try again.", "danger")
        return redirect(url_for("profile"))

    finally:
        cursor.close()
        connection.close()



@app.route("/expenses/<int:user_id>", methods=["GET", "POST"])
@login_required
def expenses(user_id):

    if request.method == "POST":

        expense_name = request.form["expense_name"]
        category = request.form["category"]
        amount = request.form["amount"]
        expense_date = request.form["expense_date"]

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO expenses
            (user_id, expense_name, category, amount, expense_date)
            VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            expense_name,
            category,
            amount,
            expense_date
        )

        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("expenses", user_id=user_id))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM expenses
        WHERE user_id = %s
        ORDER BY expense_date DESC, id DESC
    """, (user_id,))

    expense_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "expenses.html",
        expenses=expense_list,
        user_id=user_id
    )


@app.route("/dashboard/<int:user_id>")
@login_required
def dashboard(user_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # --------------------------------
    # User Information
    # --------------------------------

    cursor.execute("""
        SELECT *
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cursor.fetchone()

    # --------------------------------
    # Total Expenses
    # --------------------------------

    cursor.execute("""
        SELECT
            COALESCE(SUM(amount), 0) AS total_expenses
        FROM expenses
        WHERE user_id = %s
    """, (user_id,))

    expense_result = cursor.fetchone()

    total_expenses = float(
        expense_result["total_expenses"]
    )

    # --------------------------------
    # Monthly Income
    # --------------------------------

    monthly_income = float(
        user["monthly_income"]
    ) if user else 0

    # --------------------------------
    # Savings
    # --------------------------------

    savings = (
        monthly_income - total_expenses
    )

    # --------------------------------
    # Saving Rate
    # --------------------------------

    if monthly_income > 0:

        saving_rate = (
            savings / monthly_income
        ) * 100

    else:

        saving_rate = 0

    # --------------------------------
    # Financial Health
    # --------------------------------

    if saving_rate >= 40:

        financial_health = "Healthy"

    elif saving_rate >= 20:

        financial_health = "Moderate"

    else:

        financial_health = "Needs Attention"

    # --------------------------------
    # Financial Insights
    # --------------------------------

    insights = []

    if saving_rate >= 40:

        insights.append(
            "Your savings rate is strong. Continue maintaining your current saving habit."
        )

    elif saving_rate >= 20:

        insights.append(
            "Your savings rate is moderate. Try to increase your monthly savings gradually."
        )

    else:

        insights.append(
            "Your savings rate is low. Review your expenses and reduce unnecessary spending."
        )

    if total_expenses > monthly_income:

        insights.append(
            "Your expenses are higher than your monthly income. Immediate expense reduction is recommended."
        )

    if savings > 0:

        insights.append(
            f"You currently have ₹{savings:.2f} available as monthly savings."
        )

    else:

        insights.append(
            "You currently have no positive monthly savings."
        )

    # --------------------------------
    # Monthly Expense Analysis
    # --------------------------------

    cursor.execute("""
        SELECT
            DATE_FORMAT(expense_date, '%Y-%m') AS month,
            SUM(amount) AS monthly_expense
        FROM expenses
        WHERE user_id = %s
        GROUP BY DATE_FORMAT(expense_date, '%Y-%m')
        ORDER BY month
    """, (user_id,))

    monthly_data = cursor.fetchall()

    # --------------------------------
    # Prepare Monthly Chart Data
    # --------------------------------

    months = []

    monthly_savings = []
    monthly_expenses = []

    for item in monthly_data:

        month = item["month"]

        monthly_expense = float(
            item["monthly_expense"]
        )

        month_saving = (
            monthly_income - monthly_expense
        )

        months.append(month)

        monthly_savings.append(
            month_saving
        )
        monthly_expenses.append(
            monthly_expense
        )

    # --------------------------------
    # Close Database
    # --------------------------------

    cursor.close()
    connection.close()

    # --------------------------------
    # Render Dashboard
    # --------------------------------

    return render_template(

        "dashboard.html",

        user_id=user_id,

        user=user,

        total_expenses=total_expenses,

        savings=savings,

        saving_rate=saving_rate,

        financial_health=financial_health,

        months=months,

        monthly_savings=monthly_savings,

        monthly_expenses=monthly_expenses,


        insights=insights

    )

@app.route("/analytics/<int:user_id>")
@login_required
def analytics(user_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # --------------------------------
    # Get User
    # --------------------------------

    cursor.execute("""
        SELECT *
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cursor.fetchone()

    # --------------------------------
    # Category-wise Expenses
    # --------------------------------

    cursor.execute("""
        SELECT
            category,
            SUM(amount) AS total_amount
        FROM expenses
        WHERE user_id = %s
        GROUP BY category
        ORDER BY total_amount DESC
    """, (user_id,))

    category_data = cursor.fetchall()

    # Convert Decimal to float
    for item in category_data:
        item["total_amount"] = float(
            item["total_amount"]
        )

    # --------------------------------
    # Total Expenses
    # --------------------------------

    cursor.execute("""
        SELECT
            COALESCE(SUM(amount), 0) AS total_expenses
        FROM expenses
        WHERE user_id = %s
    """, (user_id,))

    result = cursor.fetchone()

    total_expenses = float(
        result["total_expenses"]
    )

    # --------------------------------
    # Calculate Percentage
    # --------------------------------

    for item in category_data:

        if total_expenses > 0:

            item["percentage"] = (
                item["total_amount"]
                / total_expenses
            ) * 100

        else:

            item["percentage"] = 0

    # --------------------------------
    # Highest Expense Category
    # --------------------------------

    highest_category = None

    if category_data:
        highest_category = category_data[0]

    # --------------------------------
    # Reducible Expenses
    # --------------------------------

    reducible_categories = [
        "Shopping",
        "Entertainment",
        "Other"
    ]

    reducible_expenses = 0

    for item in category_data:

        if item["category"] in reducible_categories:

            reducible_expenses += (
                item["total_amount"]
            )

    potential_saving = (
        reducible_expenses * 0.20
    )

    # --------------------------------
    # Expense Reduction Recommendations
    # --------------------------------

    recommendations = []

    for item in category_data:

        category_name = item["category"]
        amount = item["total_amount"]

        if category_name in reducible_categories:

            possible_saving = amount * 0.20

            recommendations.append({

                "category": category_name,

                "amount": amount,

                "possible_saving": possible_saving,

                "message":
                    f"Consider reducing "
                    f"{category_name} expenses "
                    f"by around 20%."

            })

    # --------------------------------
    # Close Database
    # --------------------------------

    cursor.close()
    connection.close()

    # --------------------------------
    # Render Analytics
    # --------------------------------

    return render_template(

        "analytics.html",

        user=user,

        user_id=user_id,

        category_data=category_data,

        total_expenses=total_expenses,

        highest_category=highest_category,

        reducible_expenses=reducible_expenses,

        potential_saving=potential_saving,

        recommendations=recommendations

    )
@app.route("/goals/<int:user_id>", methods=["GET", "POST"])
@login_required
def goals(user_id):

    if request.method == "POST":

        goal_name = request.form["goal_name"]
        target_amount = float(request.form["target_amount"])
        current_amount = float(request.form["current_amount"])
        target_months = int(request.form["target_months"])

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO financial_goals
            (user_id, goal_name, target_amount, current_amount, target_months)
            VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            goal_name,
            target_amount,
            current_amount,
            target_months
        )

        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "goals",
                user_id=user_id
            )
        )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # --------------------------------
    # Get User Financial Information
    # --------------------------------

    cursor.execute("""
        SELECT monthly_income, risk_preference
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cursor.fetchone()

    monthly_income = float(
        user["monthly_income"]
    ) if user else 0

    risk_preference = (
        user["risk_preference"]
        if user and user["risk_preference"]
        else "Medium"
    )


    # --------------------------------
    # Calculate Current Monthly Expense
    # --------------------------------

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_expenses
        FROM expenses
        WHERE user_id = %s
    """, (user_id,))

    expense_data = cursor.fetchone()

    monthly_expenses = float(
        expense_data["total_expenses"]
    )


    # --------------------------------
    # Available Monthly Surplus
    # --------------------------------

    monthly_surplus = max(
        monthly_income - monthly_expenses,
        0
    )


    # --------------------------------
    # Get Financial Goals
    # --------------------------------

    cursor.execute("""
        SELECT *
        FROM financial_goals
        WHERE user_id = %s
        ORDER BY id DESC
    """, (user_id,))

    goal_list = cursor.fetchall()


    # --------------------------------
    # Investment Scenarios
    # --------------------------------

    scenarios = [

        {
            "name": "Conservative",
            "return_rate": 6
        },

        {
            "name": "Balanced",
            "return_rate": 10
        },

        {
            "name": "Growth",
            "return_rate": 12
        }

    ]


    # --------------------------------
    # Process Each Goal
    # --------------------------------

    for goal in goal_list:

        target = float(
            goal["target_amount"]
        )

        current = float(
            goal["current_amount"]
        )

        months = int(
            goal["target_months"]
        )


        # --------------------------------
        # Remaining Amount
        # --------------------------------

        remaining = max(
            target - current,
            0
        )


        # --------------------------------
        # Goal Progress
        # --------------------------------

        if target > 0:

            progress = (
                current / target
            ) * 100

        else:

            progress = 0


        # --------------------------------
        # Required Monthly Saving
        # --------------------------------

        if months > 0:

            monthly_required = (
                remaining / months
            )

        else:

            monthly_required = 0


        goal["remaining"] = remaining

        goal["monthly_required"] = monthly_required

        goal["progress"] = min(
            progress,
            100
        )


        # --------------------------------
        # Investment Scenario Analysis
        # --------------------------------

        goal["scenarios"] = []


        for scenario in scenarios:

            monthly_investment = calculate_monthly_investment(

                target,

                current,

                months,

                scenario["return_rate"]

            )


            # --------------------------------
            # Feasibility Check
            # --------------------------------

            if monthly_investment <= monthly_surplus:

                status = "Achievable"

                gap = 0

            else:

                status = "Needs Adjustment"

                gap = (
                    monthly_investment
                    - monthly_surplus
                )


            scenario_result = {

                "name": scenario["name"],

                "return_rate": scenario["return_rate"],

                "monthly_investment": monthly_investment,

                "status": status,

                "gap": gap

            }


            goal["scenarios"].append(
                scenario_result
            )


        # --------------------------------
        # Overall Recommendation
        # --------------------------------

        achievable_scenarios = [

            scenario
            for scenario in goal["scenarios"]

            if scenario["status"] == "Achievable"

        ]


        if achievable_scenarios:

            best_option = achievable_scenarios[0]

            goal["recommendation"] = (
                "Your goal is achievable "
                "with your current monthly surplus."
            )

            goal["recommended_scenario"] = (
                best_option["name"]
            )

        else:

            goal["recommendation"] = (
                "Your goal may need a longer "
                "duration or additional monthly savings."
            )

            goal["recommended_scenario"] = None


        # --------------------------------
        # Investment Recommendation
        # --------------------------------

        if months <= 12:

            time_horizon = "Short Term"

        elif months <= 36:

            time_horizon = "Medium Term"

        else:

            time_horizon = "Long Term"


        if risk_preference.lower() == "low":

            if time_horizon == "Short Term":

                recommendation = (
                    "FD / RD / Low-risk savings options"
                )

            elif time_horizon == "Medium Term":

                recommendation = (
                    "RD / Debt-oriented investment options"
                )

            else:

                recommendation = (
                    "Debt-oriented / Conservative investment options"
                )


        elif risk_preference.lower() == "medium":

            if time_horizon == "Short Term":

                recommendation = (
                    "RD / Short-term debt-oriented options"
                )

            elif time_horizon == "Medium Term":

                recommendation = (
                    "Balanced / Hybrid-oriented options"
                )

            else:

                recommendation = (
                    "Balanced mutual-fund / Hybrid-oriented options"
                )


        else:

            if time_horizon == "Short Term":

                recommendation = (
                    "Short-term diversified options; "
                    "avoid excessive risk"
                )

            elif time_horizon == "Medium Term":

                recommendation = (
                    "Diversified equity / Hybrid-oriented options"
                )

            else:

                recommendation = (
                    "Long-term diversified equity-oriented options"
                )


        goal["time_horizon"] = time_horizon

        goal["investment_recommendation"] = recommendation

        goal["risk_preference"] = risk_preference


    # --------------------------------
    # Close Database Connection
    # --------------------------------

    cursor.close()
    connection.close()


    # --------------------------------
    # Render Goals Page
    # --------------------------------

    return render_template(

        "goals.html",

        goals=goal_list,

        user_id=user_id,

        monthly_income=monthly_income,

        monthly_expenses=monthly_expenses,

        monthly_surplus=monthly_surplus

    )
@app.route("/balance-sheet/<int:user_id>")
@login_required
def balance_sheet(user_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # --------------------------------
    # Get User Income
    # --------------------------------

    cursor.execute("""
        SELECT monthly_income
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cursor.fetchone()

    monthly_income = float(
        user["monthly_income"]
    ) if user else 0


    # --------------------------------
    # Total Expenses
    # --------------------------------

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_expenses
        FROM expenses
        WHERE user_id = %s
    """, (user_id,))

    expense_data = cursor.fetchone()

    total_expenses = float(
        expense_data["total_expenses"]
    )


    # --------------------------------
    # Calculate Savings
    # --------------------------------

    savings = max(
        monthly_income - total_expenses,
        0
    )


    # --------------------------------
    # Saving Rate
    # --------------------------------

    if monthly_income > 0:

        saving_rate = (
            savings / monthly_income
        ) * 100

    else:

        saving_rate = 0


    # --------------------------------
    # Financial Health
    # --------------------------------

    if saving_rate >= 40:

        financial_health = "Healthy"

    elif saving_rate >= 20:

        financial_health = "Moderate"

    else:

        financial_health = "Needs Attention"


    # --------------------------------
    # Category-wise Expenses
    # --------------------------------

    cursor.execute("""
        SELECT
            category,
            SUM(amount) AS total_amount
        FROM expenses
        WHERE user_id = %s
        GROUP BY category
        ORDER BY total_amount DESC
    """, (user_id,))

    category_data = cursor.fetchall()
    for category in category_data:
        category["total_amount"] = float(category["total_amount"])


    # --------------------------------
    # Close Connection
    # --------------------------------

    cursor.close()
    connection.close()


    return render_template(

        "balance_sheet.html",

        user_id=user_id,

        monthly_income=monthly_income,

        total_expenses=total_expenses,

        savings=savings,

        saving_rate=saving_rate,

        financial_health=financial_health,

        category_data=category_data

    )

@app.route("/investment-planner/<int:user_id>", methods=["GET", "POST"])
@login_required
def investment_planner(user_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, monthly_income, existing_savings,
               risk_preference
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cursor.fetchone()

    if not user:
        cursor.close()
        connection.close()
        return "User not found", 404

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_expenses
        FROM expenses
        WHERE user_id = %s
    """, (user_id,))

    expense_data = cursor.fetchone()

    monthly_income = float(user["monthly_income"] or 0)
    total_expenses = float(expense_data["total_expenses"] or 0)
    monthly_surplus = max(monthly_income - total_expenses, 0)

    existing_savings = float(user["existing_savings"] or 0)
    default_risk = user["risk_preference"] or "Medium"

    cursor.close()
    connection.close()

    result = None
    error = None

    if request.method == "POST":

        try:
            monthly_amount = float(request.form["monthly_amount"])
            months = int(request.form["months"])
            risk = request.form["risk"]
            goal = request.form["goal"]

            if monthly_amount <= 0 or months <= 0:
                raise ValueError("Enter a positive amount and duration.")

            if months > 600:
                raise ValueError("Duration cannot exceed 600 months.")

            if risk not in ["Low", "Medium", "High"]:
                raise ValueError("Select a valid risk preference.")

            if goal not in [
                "Emergency Fund",
                "Education",
                "House / Flat",
                "Wealth Creation",
                "Other"
            ]:
                raise ValueError("Select a valid financial goal.")

            options = [
                {
                    "name": "Bank FD / RD",
                    "risk": "Lower",
                    "annual_rate": 6,
                    "suitable": months <= 36 or risk == "Low",
                    "description": (
                        "Consider for stability and planned goals. "
                        "Check current bank rates, terms and deposit protection."
                    )
                },
                {
                    "name": "Mutual Funds",
                    "risk": "Market-linked",
                    "annual_rate": 10,
                    "suitable": months >= 60 and risk in ["Medium", "High"],
                    "description": (
                        "Diversified funds may suit longer horizons, "
                        "but market value can fall and returns are not guaranteed."
                    )
                },
                {
                    "name": "Stocks",
                    "risk": "High",
                    "annual_rate": 12,
                    "suitable": months >= 60 and risk == "High",
                    "description": (
                        "Direct shares can be volatile. Learn about diversification "
                        "and avoid investing money needed soon."
                    )
                },
                {
                    "name": "Gold",
                    "risk": "Price fluctuation",
                    "annual_rate": 7,
                    "suitable": months >= 36,
                    "description": (
                        "Gold can diversify a portfolio, but prices fluctuate "
                        "and costs vary by investment method."
                    )
                },
                {
                    "name": "Plot / Flat",
                    "risk": "High capital and liquidity risk",
                    "annual_rate": None,
                    "suitable": False,
                    "description": (
                        "Usually requires substantial capital and has legal, "
                        "maintenance and transaction costs. Compare these before investing."
                    )
                }
            ]

            for option in options:
                rate = option["annual_rate"]

                if rate is not None:
                    monthly_rate = (rate / 100) / 12

                    if monthly_rate == 0:
                        future_value = monthly_amount * months
                    else:
                        future_value = (
                            monthly_amount
                            * (((1 + monthly_rate) ** months - 1) / monthly_rate)
                        )

                    option["estimated_value"] = round(future_value, 2)
                    option["estimated_contributions"] = round(
                        monthly_amount * months, 2
                    )
                else:
                    option["estimated_value"] = None
                    option["estimated_contributions"] = round(
                        monthly_amount * months, 2
                    )

            suitable_options = [
                option for option in options if option["suitable"]
            ]

            result = {
                "monthly_amount": monthly_amount,
                "months": months,
                "risk": risk,
                "goal": goal,
                "options": options,
                "suitable_options": suitable_options,
                "budget_ok": monthly_amount <= monthly_surplus
            }
            
    # Personalized educational suggestions
            if risk_preference == "Low":

                recommended_options = [
                "Bank FD / RD",
                "Gold"
            ]

                recommendation_message = (
                "You prefer lower risk. Compare bank deposits "
                "and other suitable lower-risk options. Gold prices "
                "can fluctuate, so it is not risk-free."
        )

            elif risk_preference == "Medium":

                recommended_options = [
                "Bank FD / RD",
                "Mutual Funds",
                "Gold"
            ]

                recommendation_message = (
                "You prefer moderate risk. Compare stability, "
                "diversification, liquidity and investment duration "
                "before selecting an option."
            )

            else:

                recommended_options = [
                "Mutual Funds",
                "Stocks",
                "Gold"
            ]

            recommendation_message = (
                "You prefer higher risk. Diversification and "
                "understanding potential losses are important. "
                "Higher risk does not guarantee higher returns."
            )

        except (ValueError, TypeError, KeyError) as exc:
            error = str(exc) or "Please enter valid values."

    return render_template(
        "investment_planner.html",
        user=user,
        user_id=user_id,
        monthly_income=monthly_income,
        total_expenses=total_expenses,
        monthly_surplus=monthly_surplus,
        existing_savings=existing_savings,
        default_risk=default_risk,
        result=result,
        error=error,
        recommended_options=recommended_options,
        recommendation_message=recommendation_message
    )

@app.route("/export-report/<int:user_id>")
@login_required
def export_report(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT name, monthly_income, existing_savings,
                   risk_preference
            FROM users
            WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()

        if not user:
            return "User not found", 404

        cursor.execute("""
            SELECT expense_name, category, amount, expense_date
            FROM expenses
            WHERE user_id = %s
            ORDER BY expense_date DESC
        """, (user_id,))
        expenses = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["FinSight Financial Report"])
        writer.writerow(["Name", user["name"]])
        writer.writerow(["Monthly Income", user["monthly_income"]])
        writer.writerow(["Existing Savings", user["existing_savings"]])
        writer.writerow(["Risk Preference", user["risk_preference"]])
        writer.writerow([])
        writer.writerow([
            "Expense Name", "Category", "Amount", "Date"
        ])

        for expense in expenses:
            writer.writerow([
                expense["expense_name"],
                expense["category"],
                expense["amount"],
                expense["expense_date"]
            ])

        file_data = io.BytesIO(
            output.getvalue().encode("utf-8-sig")
        )

        return send_file(
            file_data,
            mimetype="text/csv",
            as_attachment=True,
            download_name="FinSight_Financial_Report.csv"
        )

    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    app.run(debug=True)