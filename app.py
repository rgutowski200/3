import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import io

from db import supabase

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

st.set_page_config(page_title="Retirement Decision Engine", layout="wide")


def auth_box():
    if "user" not in st.session_state:
        st.session_state.user = None

    # Top-page account bar instead of left sidebar sign-in.
    st.markdown("""
    <style>
    .account-bar {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 18px;
        background: #ffffff;
        box-shadow: 0 1px 8px rgba(15, 23, 42, 0.04);
    }
    .account-pill {
        display: inline-block;
        padding: 5px 11px;
        border-radius: 999px;
        background: #dcfce7;
        color: #15803d;
        font-size: 0.82rem;
        font-weight: 800;
        margin-right: 8px;
    }
    .signed-out-pill {
        display: inline-block;
        padding: 5px 11px;
        border-radius: 999px;
        background: #fee2e2;
        color: #b91c1c;
        font-size: 0.82rem;
        font-weight: 800;
        margin-right: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.user:
        with st.container():
            left, right = st.columns([5, 1])
            with left:
                st.markdown(
                    f"""
                    <div class="account-bar">
                        <span class="account-pill">Signed In</span>
                        <strong>{st.session_state.user.email}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with right:
                st.write("")
                if st.button("Logout", use_container_width=True):
                    supabase.auth.sign_out()
                    st.session_state.user = None
                    st.rerun()

        return st.session_state.user

    with st.expander("Sign in or create an account", expanded=False):
        st.markdown(
            "<span class='signed-out-pill'>Not Signed In</span> Sign in to save and load scenarios.",
            unsafe_allow_html=True
        )

        mode = st.radio(
            "Account action",
            ["Login", "Create Account"],
            horizontal=True
        )

        c1, c2, c3 = st.columns([2, 2, 1])

        with c1:
            email = st.text_input("Email")
        with c2:
            password = st.text_input("Password", type="password")
        with c3:
            st.write("")
            st.write("")
            action_clicked = st.button(mode, use_container_width=True)

        if action_clicked:
            if not email or not password:
                st.error("Enter both email and password.")
            elif mode == "Create Account":
                try:
                    supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    st.success("Account created. Check email if confirmation is required.")
                except Exception as e:
                    st.error(f"Create account failed: {e}")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    st.session_state.user = res.user
                    st.success("Logged in.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    return st.session_state.user


user = auth_box()

st.title("Retirement Decision Engine - Guided Planner")
st.caption("Guided retirement planner with detailed budget, spouse planning, simple/advanced income builder, 2-bucket withdrawals, RTV scoring, saved scenarios, and iPad-friendly AI chat.")


def money(x):
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return "$0"




def calculate_risk_scores(summary):
    sequence_risk = max(0, min(100, round(summary["rough_wr"] * 1200)))
    tax_risk = 85 if summary["traditional"] > summary["roth"] * 4 else 55
    healthcare_risk = 75 if summary["retire_age"] < 65 else 40
    longevity_risk = 70 if summary["end_age"] >= 95 else 45
    income_risk = max(0, 100 - round(summary["income_coverage"] * 100))

    return {
        "Sequence Risk": sequence_risk,
        "Tax Risk": tax_risk,
        "Healthcare Risk": healthcare_risk,
        "Longevity Risk": longevity_risk,
        "Income Stability Risk": income_risk,
    }


def explain_scenario_changes(current_summary, compare_summary):
    changes = []

    score_diff = current_summary["score"] - compare_summary["score"]

    if current_summary["retire_age"] > compare_summary["retire_age"]:
        changes.append(
            f"Retirement age increased from {compare_summary['retire_age']} to "
            f"{current_summary['retire_age']}, improving portfolio longevity."
        )

    elif current_summary["retire_age"] < compare_summary["retire_age"]:
        changes.append(
            f"Earlier retirement increased pressure on the portfolio."
        )

    spending_diff = current_summary["monthly_spending"] - compare_summary["monthly_spending"]

    if spending_diff < -500:
        changes.append(
            f"Monthly spending decreased by {money(abs(spending_diff))}, helping improve retirement sustainability."
        )

    elif spending_diff > 500:
        changes.append(
            f"Monthly spending increased by {money(spending_diff)}, creating more max withdrawal rate."
        )

    assets_diff = current_summary["total_assets"] - compare_summary["total_assets"]

    if assets_diff > 50000:
        changes.append(
            f"Total investable assets increased by {money(assets_diff)}, strengthening retirement flexibility."
        )

    income_diff = current_summary["annual_income"] - compare_summary["annual_income"]

    if income_diff > 5000:
        changes.append(
            f"Guaranteed and outside income increased by {money(income_diff)} annually."
        )

    wr_diff = current_summary["rough_wr"] - compare_summary["rough_wr"]

    if wr_diff < -0.005:
        changes.append(
            f"Estimated max withdrawal rate improved from {pct(compare_summary['rough_wr'])} "
            f"to {pct(current_summary['rough_wr'])}."
        )

    elif wr_diff > 0.005:
        changes.append(
            f"Estimated max withdrawal rate increased from {pct(compare_summary['rough_wr'])} "
            f"to {pct(current_summary['rough_wr'])}."
        )

    if not changes:
        changes.append("No major structural differences were detected between these scenarios.")

    headline = (
        f"RTV changed from {compare_summary['score']} to {current_summary['score']} "
        f"({score_diff:+} points)."
    )

    return headline, changes

def pct(x):
    try:
        return f"{float(x):.1%}"
    except Exception:
        return "0.0%"


# -----------------------------
# User Help / Tooltips
# -----------------------------
FIELD_HELP = {
    "current_age": "Enter your current age today. This is the starting age for the retirement projection.",
    "retire_age": "Enter the age you want to stop working or begin relying on retirement income.",
    "end_age": "Enter the age the plan should last through. Many people use 90, 95, or 100 for conservative planning.",
    "traditional": "Total balance in pre-tax accounts such as traditional 401(k), traditional IRA, 403(b), or rollover IRA.",
    "roth": "Total balance in Roth accounts such as Roth IRA or Roth 401(k). These are generally tax-free in retirement if rules are met.",
    "taxable": "Total balance in regular brokerage or investment accounts outside retirement accounts.",
    "cash": "Cash, CDs, money market, short-term bonds, or other safer assets used as Bucket 1.",
    "annual_contribution": "How much you expect to add to retirement accounts each year until retirement.",
    "healthcare": "Estimated annual healthcare cost after retirement before Medicare or in addition to Medicare.",
    "user_ss_age": "Age when you expect to start Social Security. Earlier usually means lower benefits; later usually means higher benefits.",
    "user_ss": "Estimated annual Social Security benefit in today’s dollars.",
    "growth_return": "Expected annual return for growth assets. This is only an assumption, not a guarantee.",
    "safe_return": "Expected annual return for Bucket 1 or safer assets.",
    "inflation": "Expected annual inflation rate used to increase future spending.",
    "annual_conversion": "Annual amount to test moving from traditional retirement accounts into Roth accounts.",
    "bucket1_years": "How many years of spending you want protected in safer assets.",
    "flat_monthly_spending": "Your estimated monthly lifestyle spending before healthcare. Do not include retirement contributions.",
    "survivor_spending": "Optional annual spending estimate after one spouse passes away.",
    "simple_income": "Other annual income besides Social Security, such as pension, rent, consulting, or part-time work.",
    "simple_income_start": "Age when this other income begins.",
    "simple_income_end": "Age when this income ends. Use 0 if it continues for life.",
    "simple_income_inflation": "Check this if the income is expected to rise with inflation.",
    "simple_income_reliability": "Guaranteed means reliable income like pension. Variable means uncertain income like side work.",
    "spouse_age": "Your spouse or partner’s current age.",
    "spouse_retire_age": "Age your spouse or partner expects to retire.",
    "spouse_plan_age": "Age your spouse’s part of the plan should last through.",
    "spouse_annual_contribution": "Spouse or partner’s expected annual retirement contributions before retirement.",
    "spouse_healthcare": "Estimated spouse or partner annual healthcare cost in retirement.",
    "spouse_ss_age": "Age when spouse or partner expects to start Social Security.",
    "spouse_ss": "Estimated annual spouse or partner Social Security benefit.",
}

def page_help(title, body):
    with st.expander(f"💬 What this page means: {title}", expanded=False):
        st.write(body)

def section_note(text):
    st.info(f"💬 {text}")



def set_default(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


# -----------------------------
# Defaults
# -----------------------------
defaults = {
    "current_age": 0,
    "retire_age": 0,
    "end_age": 90,
    "traditional": 0,
    "roth": 0,
    "taxable": 0,
    "cash": 0,
    "annual_contribution": 0,
    "has_spouse": False,
    "spouse_age": 0,
    "spouse_retire_age": 0,
    "spouse_plan_age": 90,
    "spouse_annual_contribution": 0,
    "healthcare": 0,
    "spouse_healthcare": 0,
    "user_ss_age": 62,
    "user_ss": 0,
    "spouse_ss_age": 62,
    "spouse_ss": 0,
    "survivor_ss_strategy": "Higher benefit continues",
    "survivor_spending": 0,
    "budget_mode": "Flat monthly number",
    "flat_monthly_spending": 0,
    "growth_return": 0.07,
    "safe_return": 0.045,
    "inflation": 0.03,
    "annual_conversion": 0,
    "bucket1_years": 3.0,
    "income_mode": "Simple income",
    "simple_income": 0,
    "simple_income_start": 0,
    "simple_income_end": 0,
    "simple_income_inflation": False,
    "simple_income_reliability": "Guaranteed",
    "home_value": 0,
    "mortgage_balance": 0,
    "monthly_mortgage": 0,
    "annual_property_taxes_home": 0,
    "mortgage_payoff_age": 0,
    "retirement_housing_plan": "Unsure",
    "enable_spending_change": False,
    "spending_change_age": 0,
    "spending_change_monthly": 0,
}
for k, v in defaults.items():
    set_default(k, v)

budget_keys = [
    ("mortgage_rent", "Mortgage / Rent"),
    ("property_tax", "Property taxes"),
    ("home_insurance", "Home insurance"),
    ("hoa", "HOA / condo fees"),
    ("electric", "Electric"),
    ("gas_utility", "Gas / heating"),
    ("water_sewer", "Water / sewer"),
    ("trash", "Trash"),
    ("internet", "Internet"),
    ("cell_phone", "Cell phones"),
    ("subscriptions", "Streaming / subscriptions"),
    ("groceries", "Groceries"),
    ("restaurants", "Restaurants / coffee"),
    ("household_items", "Household items"),
    ("car_payment", "Car payments"),
    ("car_insurance", "Car insurance"),
    ("gasoline", "Gasoline"),
    ("car_maintenance", "Car maintenance"),
    ("travel", "Vacations / travel"),
    ("hobbies", "Hobbies"),
    ("golf_entertainment", "Golf / entertainment"),
    ("clothing", "Clothing"),
    ("gifts_family", "Gifts / family support"),
    ("pets", "Pets"),
    ("personal_care", "Personal care"),
    ("medical_oop", "Medical out-of-pocket, not premiums"),
    ("misc_buffer", "Miscellaneous buffer"),
]
for k, _ in budget_keys:
    set_default(k, 0)

if "income_sources_df" not in st.session_state:
    st.session_state.income_sources_df = pd.DataFrame([
        {
            "Name": "Pension / side gig / rental",
            "Annual Amount": 0,
            "Start Age": 0,
            "End Age": 0,
            "Inflation Adjusted": False,
            "Taxable": True,
            "Owner": "Joint",
            "Reliability": "Guaranteed",
            "Continues After First Death": True,
        }
    ])


# -----------------------------
# Saved scenario helpers
# -----------------------------
def get_scenario_data():
    data = {}

    keys_to_save = [
        "current_age", "retire_age", "end_age",
        "traditional", "roth", "taxable", "cash",
        "annual_contribution", "has_spouse", "spouse_age",
        "spouse_retire_age", "spouse_plan_age",
        "spouse_annual_contribution", "healthcare", "spouse_healthcare",
        "user_ss_age", "user_ss", "spouse_ss_age", "spouse_ss",
        "survivor_ss_strategy", "survivor_spending",
        "budget_mode", "flat_monthly_spending",
        "growth_return", "safe_return", "inflation",
        "annual_conversion", "bucket1_years",
        "income_mode", "simple_income", "simple_income_start",
        "simple_income_end", "simple_income_inflation",
        "simple_income_reliability",
        "home_value", "mortgage_balance", "monthly_mortgage",
        "annual_property_taxes_home", "mortgage_payoff_age",
        "retirement_housing_plan",
        "enable_spending_change", "spending_change_age", "spending_change_monthly",
    ]

    for key in keys_to_save:
        data[key] = st.session_state.get(key)

    for key, _ in budget_keys:
        data[key] = st.session_state.get(key, 0)

    if "income_sources_df" in st.session_state and st.session_state.income_sources_df is not None:
        data["income_sources_df"] = st.session_state.income_sources_df.to_dict("records")
    else:
        data["income_sources_df"] = []

    return data


def apply_scenario_data(data):
    for key, value in data.items():
        if key == "income_sources_df":
            st.session_state.income_sources_df = pd.DataFrame(value)
        else:
            st.session_state[key] = value


def save_scenario(user, scenario_name, scenario_data):
    supabase.table("retirement_scenarios").insert({
        "user_id": user.id,
        "scenario_name": scenario_name,
        "scenario_data": scenario_data
    }).execute()


def load_scenarios(user):
    response = (
        supabase.table("retirement_scenarios")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def detailed_monthly_budget_total():
    return sum(float(st.session_state.get(k, 0) or 0) for k, _ in budget_keys)


def annual_household_spending():
    if st.session_state.budget_mode == "Flat monthly number":
        return float(st.session_state.flat_monthly_spending or 0) * 12
    return detailed_monthly_budget_total() * 12


def annual_spending_for_age(age):
    base = annual_household_spending()
    if bool(st.session_state.get("enable_spending_change", False)):
        change_age = int(st.session_state.get("spending_change_age", 0) or 0)
        change_monthly = float(st.session_state.get("spending_change_monthly", 0) or 0)
        if change_age > 0 and change_monthly > 0 and age >= change_age:
            return change_monthly * 12
    return base


def home_equity():
    return max(float(st.session_state.home_value or 0) - float(st.session_state.mortgage_balance or 0), 0)


def annual_mortgage_payment_for_age(age):
    monthly = float(st.session_state.monthly_mortgage or 0)
    payoff_age = int(st.session_state.mortgage_payoff_age or 0)
    if monthly <= 0:
        return 0
    if payoff_age <= 0:
        return monthly * 12
    if age < payoff_age:
        return monthly * 12
    return 0


def housing_flexibility_label():
    equity = home_equity()
    plan = st.session_state.retirement_housing_plan
    if equity >= 500000:
        return "High Flexibility"
    if equity >= 250000:
        return "Moderate Flexibility"
    if plan in ["Downsize", "Relocate", "Snowbird"]:
        return "Strategy Opportunity"
    return "Limited / Unknown"


def required_missing():
    missing = []

    if st.session_state.current_age == 0:
        missing.append("current age")
    if st.session_state.retire_age == 0:
        missing.append("retirement age")
    if st.session_state.end_age == 0:
        missing.append("plan-through age")
    if annual_household_spending() == 0:
        missing.append("household spending")

    # Spouse fields are only required when the user chooses to include a spouse/partner.
    if st.session_state.has_spouse:
        if st.session_state.spouse_age == 0:
            missing.append("spouse age")
        if st.session_state.spouse_retire_age == 0:
            missing.append("spouse retirement age")

    return missing


def inflate(amount, start_age, age):
    if age <= start_age:
        return amount
    return amount * ((1 + float(st.session_state.inflation)) ** (age - start_age))


def simple_income_for_age(age):
    amount = float(st.session_state.simple_income or 0)
    start = int(st.session_state.simple_income_start or 0)
    end = int(st.session_state.simple_income_end or 0)
    if amount <= 0 or start <= 0 or age < start:
        return {"guaranteed": 0, "variable": 0, "taxable": 0, "total": 0}
    if end > 0 and age > end:
        return {"guaranteed": 0, "variable": 0, "taxable": 0, "total": 0}
    val = inflate(amount, start, age) if st.session_state.simple_income_inflation else amount
    if st.session_state.simple_income_reliability == "Guaranteed":
        return {"guaranteed": val, "variable": 0, "taxable": val, "total": val}
    return {"guaranteed": 0, "variable": val, "taxable": val, "total": val}


def advanced_income_for_age(age, spouse_alive):
    df = st.session_state.income_sources_df
    guaranteed = variable = taxable = total = 0.0
    if df is None or df.empty:
        return {"guaranteed": 0, "variable": 0, "taxable": 0, "total": 0}

    for _, row in df.iterrows():
        try:
            amount = float(row.get("Annual Amount", 0) or 0)
            start = int(row.get("Start Age", 0) or 0)
            end = int(row.get("End Age", 0) or 0)
        except Exception:
            continue
        if amount <= 0 or start <= 0 or age < start:
            continue
        if end > 0 and age > end:
            continue

        owner = row.get("Owner", "Joint")
        continues = bool(row.get("Continues After First Death", True))
        if st.session_state.has_spouse and not spouse_alive and owner in ["Spouse", "Joint"] and not continues:
            continue

        val = inflate(amount, start, age) if bool(row.get("Inflation Adjusted", False)) else amount
        total += val
        if bool(row.get("Taxable", True)):
            taxable += val
        if row.get("Reliability", "Guaranteed") == "Guaranteed":
            guaranteed += val
        else:
            variable += val

    return {"guaranteed": guaranteed, "variable": variable, "taxable": taxable, "total": total}


def other_income_for_age(age, spouse_alive):
    if st.session_state.income_mode == "Simple income":
        return simple_income_for_age(age)
    return advanced_income_for_age(age, spouse_alive)


def calculate_rtv_score(df):
    """
    RTV = Retirement Timing Viability.

    This version prioritizes actual projected plan success:
    - Does the plan run out of money?
    - Is there any unmet spending need?
    - How large is the ending cushion?
    - Are withdrawals aggressive relative to survivability?

    A plan ending with a very large balance should score strongly even if
    outside income coverage is low or early withdrawals are elevated.
    """
    if df.empty:
        return 0, "Incomplete", []

    ending = float(df["End Total"].iloc[-1])
    start_total = float(df["Start Total"].iloc[0])
    max_wr = float(df["Withdrawal Rate"].max())
    avg_wr = float(df["Withdrawal Rate"].mean())
    income_coverage = float(df["Income Coverage Ratio"].mean())
    unmet_need = float(df["Unmet Need"].sum())

    score = 100
    reasons = []

    # Hard penalties only when the plan actually fails.
    if unmet_need > 0:
        score -= 45
        reasons.append("The plan has unmet spending needs in at least one year.")

    if ending <= 0:
        score -= 45
        reasons.append("The portfolio is depleted before the plan ends.")

    # Ending cushion is the most important success signal.
    if ending > 0 and unmet_need <= 0:
        if ending >= start_total * 2:
            score += 5
            reasons.append("Projected ending portfolio is very strong.")
        elif ending >= start_total:
            reasons.append("Projected ending portfolio remains above the starting balance.")
        elif ending >= 500000:
            score -= 3
            reasons.append("Projected ending portfolio remains healthy.")
        elif ending >= 250000:
            score -= 8
            reasons.append("Projected ending portfolio cushion is moderate.")
        else:
            score -= 18
            reasons.append("Projected ending portfolio cushion is low.")

    # Withdrawal rate matters, but should not dominate if the plan survives with a large cushion.
    if max_wr > 0.09:
        score -= 12
        reasons.append("Maximum withdrawal rate is high in at least one year.")
    elif max_wr > 0.07:
        score -= 8
        reasons.append("Maximum withdrawal rate is elevated.")
    elif max_wr > 0.05:
        score -= 4
        reasons.append("Maximum withdrawal rate is moderately elevated.")

    if avg_wr > 0.06:
        score -= 8
        reasons.append("Average withdrawal pressure is high across the plan.")
    elif avg_wr > 0.045:
        score -= 4
        reasons.append("Average withdrawal pressure is moderate.")

    # Income coverage is a confidence factor, not a deal-breaker.
    if income_coverage < 0.25:
        score -= 4
        reasons.append("Outside income covers a smaller share of spending, so the plan relies more on portfolio withdrawals.")
    elif income_coverage >= 0.60:
        score += 3
        reasons.append("Outside income coverage improves plan stability.")

    score = max(0, min(100, round(score)))

    if score >= 90:
        label = "Very Strong"
    elif score >= 80:
        label = "Strong"
    elif score >= 70:
        label = "Likely Viable"
    elif score >= 60:
        label = "Needs Optimization"
    else:
        label = "High Risk"

    return score, label, reasons

def run_projection():
    if st.session_state.current_age <= 0 or st.session_state.retire_age <= 0 or st.session_state.end_age <= 0:
        return pd.DataFrame()

    rows = []
    trad = float(st.session_state.traditional)
    roth = float(st.session_state.roth)
    taxable = float(st.session_state.taxable)
    bucket1 = float(st.session_state.cash)
    base_spending = annual_household_spending()

    for age in range(int(st.session_state.current_age), int(st.session_state.end_age) + 1):
        year_offset = age - int(st.session_state.current_age)
        spouse_age = int(st.session_state.spouse_age) + year_offset if st.session_state.has_spouse else 0
        spouse_alive = bool(st.session_state.has_spouse and spouse_age <= int(st.session_state.spouse_plan_age))
        start_total = trad + roth + taxable + bucket1

        if age < int(st.session_state.retire_age):
            trad += float(st.session_state.annual_contribution) * 0.8
            roth += float(st.session_state.annual_contribution) * 0.2
        if spouse_alive and spouse_age < int(st.session_state.spouse_retire_age):
            trad += float(st.session_state.spouse_annual_contribution) * 0.8
            roth += float(st.session_state.spouse_annual_contribution) * 0.2

        trad *= (1 + float(st.session_state.growth_return))
        roth *= (1 + float(st.session_state.growth_return))
        taxable *= (1 + float(st.session_state.growth_return))
        bucket1 *= (1 + float(st.session_state.safe_return))

        household_retired = age >= int(st.session_state.retire_age) and (not spouse_alive or spouse_age >= int(st.session_state.spouse_retire_age))

        if household_retired and bucket1 <= 0 and base_spending > 0:
            target = annual_spending_for_age(age) * float(st.session_state.bucket1_years)
            transfer = min(trad, target)
            trad -= transfer
            bucket1 += transfer * 0.80

        conversion = 0
        if age >= int(st.session_state.retire_age) and float(st.session_state.annual_conversion) > 0:
            conversion = min(trad, float(st.session_state.annual_conversion))
            trad -= conversion
            roth += conversion

        user_ss = float(st.session_state.user_ss) if age >= int(st.session_state.user_ss_age) else 0
        spouse_ss = float(st.session_state.spouse_ss) if spouse_alive and spouse_age >= int(st.session_state.spouse_ss_age) else 0
        if st.session_state.has_spouse and not spouse_alive:
            if st.session_state.survivor_ss_strategy == "Higher benefit continues":
                ss_income = max(user_ss, float(st.session_state.spouse_ss))
            else:
                ss_income = user_ss
        else:
            ss_income = user_ss + spouse_ss

        inc = other_income_for_age(age, spouse_alive)
        other_income = inc["total"]
        guaranteed_income = ss_income + inc["guaranteed"]
        variable_income = inc["variable"]

        spending = 0
        if household_retired:
            years_retired = max(age - int(st.session_state.retire_age), 0)
            if st.session_state.has_spouse and not spouse_alive and float(st.session_state.survivor_spending) > 0:
                spending = float(st.session_state.survivor_spending) * ((1 + float(st.session_state.inflation)) ** years_retired)
            else:
                spending = annual_spending_for_age(age) * ((1 + float(st.session_state.inflation)) ** years_retired)

        healthcare = 0
        if age >= int(st.session_state.retire_age):
            healthcare += float(st.session_state.healthcare)
        if spouse_alive and spouse_age >= int(st.session_state.spouse_retire_age):
            healthcare += float(st.session_state.spouse_healthcare)

        mortgage_payment = annual_mortgage_payment_for_age(age) if household_retired else 0
        total_spending = spending + healthcare + mortgage_payment
        non_portfolio_income = ss_income + other_income
        income_gap = max(total_spending - non_portfolio_income, 0)
        withdrawal_needed = income_gap

        used_b1 = used_taxable = used_trad = used_roth = 0.0
        take = min(bucket1, withdrawal_needed); bucket1 -= take; withdrawal_needed -= take; used_b1 += take
        take = min(taxable, withdrawal_needed); taxable -= take; withdrawal_needed -= take; used_taxable += take
        if withdrawal_needed > 0:
            gross_needed = withdrawal_needed / 0.80
            take = min(trad, gross_needed)
            trad -= take
            withdrawal_needed -= take * 0.80
            used_trad += take
        take = min(roth, max(withdrawal_needed, 0)); roth -= take; withdrawal_needed -= take; used_roth += take

        actual_withdrawal = used_b1 + used_taxable + used_trad + used_roth
        end_total = trad + roth + taxable + bucket1
        leftover = max(non_portfolio_income + actual_withdrawal - total_spending, 0)

        rows.append({
            "Age": age,
            "Spouse Age": spouse_age if st.session_state.has_spouse else "",
            "Spouse Alive": spouse_alive if st.session_state.has_spouse else "",
            "Household Retired": household_retired,
            "Start Total": start_total,
            "End Total": end_total,
            "Traditional": trad,
            "Roth": roth,
            "Taxable": taxable,
            "Bucket 1": bucket1,
            "Lifestyle Spending": spending,
            "Healthcare": healthcare,
            "Mortgage Payment": mortgage_payment,
            "Total Spending": total_spending,
            "Social Security": ss_income,
            "Other Guaranteed Income": inc["guaranteed"],
            "Other Variable Income": variable_income,
            "Total Other Income": other_income,
            "Total Non-Portfolio Income": non_portfolio_income,
            "Guaranteed Income": guaranteed_income,
            "Income Gap": income_gap,
            "Portfolio Withdrawal": actual_withdrawal,
            "Left Over After Spending": leftover,
            "Roth Conversion": conversion,
            "Unmet Need": max(withdrawal_needed, 0),
            "Withdrawal Rate": actual_withdrawal / max(start_total, 1),
            "Income Coverage Ratio": non_portfolio_income / max(total_spending, 1),
            "Guaranteed Income Coverage Ratio": guaranteed_income / max(total_spending, 1),
        })

        if end_total <= 0:
            break

    return pd.DataFrame(rows)



def snapshot_session_state_for_projection():
    keys = list(defaults.keys()) + [key for key, _ in budget_keys]
    snap = {}
    for key in keys:
        snap[key] = st.session_state.get(key)

    if "income_sources_df" in st.session_state and st.session_state.income_sources_df is not None:
        snap["income_sources_df"] = st.session_state.income_sources_df.copy()
    else:
        snap["income_sources_df"] = None

    return snap


def restore_session_state_after_projection(snapshot):
    for key, value in snapshot.items():
        st.session_state[key] = value


def run_projection_for_saved_scenario(data):
    snapshot = snapshot_session_state_for_projection()

    try:
        apply_scenario_data(data)
        temp_df = run_projection()

        if temp_df.empty:
            return temp_df, 0, "Incomplete", []

        score, label, reasons = calculate_rtv_score(temp_df)
        return temp_df, score, label, reasons

    finally:
        restore_session_state_after_projection(snapshot)



def test_rtv_with_changes(**changes):
    """
    Temporarily apply changes to session_state, run the real projection,
    calculate RTV, then restore original values.
    """
    snapshot = snapshot_session_state_for_projection()

    try:
        for key, value in changes.items():
            st.session_state[key] = value

        test_df = run_projection()
        if test_df.empty:
            return {
                "score": 0,
                "label": "Incomplete",
                "ending": 0,
                "max_wr": 0,
                "income_coverage": 0,
                "unmet_need": 0,
            }

        score, label, reasons = calculate_rtv_score(test_df)

        return {
            "score": score,
            "label": label,
            "ending": float(test_df["End Total"].iloc[-1]),
            "max_wr": float(test_df["Withdrawal Rate"].max()),
            "income_coverage": float(test_df["Income Coverage Ratio"].mean()),
            "unmet_need": float(test_df["Unmet Need"].sum()),
        }

    finally:
        restore_session_state_after_projection(snapshot)


def build_rtv_improvement_recommendations(base_df, base_score):
    """
    Creates practical RTV improvement options using the actual projection engine.
    """
    actions = []

    current_retire_age = int(st.session_state.retire_age)
    current_end_age = int(st.session_state.end_age)
    current_monthly = float(annual_household_spending() / 12)
    current_contrib = float(st.session_state.annual_contribution or 0)
    current_ss_age = int(st.session_state.user_ss_age)

    tests = []

    if current_monthly > 0:
        tests.append(("Reduce spending by $500/month", {"flat_monthly_spending": max(current_monthly - 500, 0)}))
        tests.append(("Reduce spending by $1,000/month", {"flat_monthly_spending": max(current_monthly - 1000, 0)}))
        tests.append(("Reduce spending by 10%", {"flat_monthly_spending": max(current_monthly * 0.90, 0)}))

    if current_retire_age < 75:
        tests.append(("Delay retirement 1 year", {"retire_age": current_retire_age + 1}))
        tests.append(("Delay retirement 2 years", {"retire_age": current_retire_age + 2}))

    if current_end_age > current_retire_age + 15:
        tests.append(("Plan to age 85 instead", {"end_age": 85}))
        tests.append(("Plan to age 90 instead", {"end_age": 90}))

    if current_contrib >= 0:
        tests.append(("Add $10,000/year contributions", {"annual_contribution": current_contrib + 10000}))
        tests.append(("Add $20,000/year contributions", {"annual_contribution": current_contrib + 20000}))

    if current_ss_age < 70:
        tests.append(("Delay your Social Security to 67", {"user_ss_age": max(67, current_ss_age)}))
        tests.append(("Delay your Social Security to 70", {"user_ss_age": 70}))

    for name, changes in tests:
        result = test_rtv_with_changes(**changes)
        delta = result["score"] - base_score

        actions.append({
            "Action": name,
            "RTV Impact": delta,
            "New RTV": result["score"],
            "Status": result["label"],
            "Ending Portfolio": result["ending"],
            "Max Withdrawal Rate": result["max_wr"],
            "Income Coverage": result["income_coverage"],
            "Unmet Need": result["unmet_need"],
        })

    actions = sorted(actions, key=lambda x: x["RTV Impact"], reverse=True)
    return actions


def build_spend_more_tests(base_score):
    """
    Tests whether user can spend more and still keep a strong RTV score.
    """
    current_monthly = float(annual_household_spending() / 12)
    if current_monthly <= 0:
        return []

    tests = [
        ("Spend $500/month more", current_monthly + 500),
        ("Spend $1,000/month more", current_monthly + 1000),
        ("Spend 10% more", current_monthly * 1.10),
        ("Spend 20% more", current_monthly * 1.20),
    ]

    rows = []
    for name, new_monthly in tests:
        result = test_rtv_with_changes(flat_monthly_spending=new_monthly)
        rows.append({
            "Scenario": name,
            "New Monthly Spending": new_monthly,
            "RTV Impact": result["score"] - base_score,
            "New RTV": result["score"],
            "Status": result["label"],
            "Ending Portfolio": result["ending"],
            "Max Withdrawal Rate": result["max_wr"],
        })

    return rows



def compact_money_label(x):
    try:
        x = float(x)
        if abs(x) >= 1_000_000:
            return f"${x/1_000_000:.1f}M"
        if abs(x) >= 1_000:
            return f"${x/1_000:.0f}K"
        return f"${x:,.0f}"
    except Exception:
        return "$0"


def style_axis_money(ax):
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: compact_money_label(x)))
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def add_last_value_label(ax, x, y, label=None):
    if len(x) == 0 or len(y) == 0:
        return
    label = label or compact_money_label(y.iloc[-1] if hasattr(y, "iloc") else y[-1])
    ax.annotate(
        label,
        xy=(x.iloc[-1] if hasattr(x, "iloc") else x[-1], y.iloc[-1] if hasattr(y, "iloc") else y[-1]),
        xytext=(8, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        fontweight="bold",
    )


def plot_portfolio_area_chart(df):
    fig, ax = plt.subplots(figsize=(12, 5.8))

    ages = df["Age"]
    stack_cols = ["Traditional", "Roth", "Taxable", "Bucket 1"]
    labels = ["Traditional", "Roth", "Taxable", "Bucket 1"]

    ax.stackplot(ages, [df[c] for c in stack_cols], labels=labels, alpha=0.82)
    ax.plot(ages, df["End Total"], linewidth=3, label="Total Portfolio")

    start_val = df["End Total"].iloc[0]
    end_val = df["End Total"].iloc[-1]

    ax.annotate(
        f"Start {compact_money_label(start_val)}",
        xy=(ages.iloc[0], start_val),
        xytext=(12, 12),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
    )

    ax.annotate(
        f"End {compact_money_label(end_val)}",
        xy=(ages.iloc[-1], end_val),
        xytext=(-90, 14),
        textcoords="offset points",
        fontsize=10,
        fontweight="bold",
    )

    ax.set_title("Portfolio Balance by Account Type", fontsize=15, fontweight="bold", loc="left")
    ax.set_xlabel("Age")
    ax.set_ylabel("Portfolio Balance")
    style_axis_money(ax)
    ax.legend(loc="upper left", ncol=3, frameon=True)
    fig.tight_layout()
    return fig


def plot_spending_income_bar_chart(df):
    fig, ax = plt.subplots(figsize=(12, 5.8))

    ages = df["Age"]
    width = 0.38

    ax.bar(ages - width / 2, df["Total Spending"], width=width, label="Total Spending")
    ax.bar(ages + width / 2, df["Total Non-Portfolio Income"], width=width, label="Non-Portfolio Income")
    ax.plot(ages, df["Portfolio Withdrawal"], linewidth=3, marker="o", markersize=4, label="Portfolio Withdrawal")

    # Label every few years to avoid clutter.
    step = max(1, len(df) // 8)
    for i in range(0, len(df), step):
        ax.text(
            ages.iloc[i],
            df["Total Spending"].iloc[i],
            compact_money_label(df["Total Spending"].iloc[i]),
            ha="center",
            va="bottom",
            fontsize=8,
        )

    add_last_value_label(ax, ages, df["Portfolio Withdrawal"], f"Withdrawal {compact_money_label(df['Portfolio Withdrawal'].iloc[-1])}")

    ax.set_title("Spending vs. Income vs. Portfolio Withdrawal", fontsize=15, fontweight="bold", loc="left")
    ax.set_xlabel("Age")
    ax.set_ylabel("Annual Amount")
    style_axis_money(ax)
    ax.legend(loc="upper left", ncol=3, frameon=True)
    fig.tight_layout()
    return fig


def plot_income_gap_chart(df):
    fig, ax = plt.subplots(figsize=(12, 5.8))

    ages = df["Age"]
    ax.bar(ages, df["Income Gap"], label="Income Gap")
    ax.plot(ages, df["Total Spending"], linewidth=3, label="Total Spending")
    ax.plot(ages, df["Guaranteed Income"], linewidth=3, label="Guaranteed Income")

    max_gap = df["Income Gap"].max()
    if max_gap > 0:
        max_gap_age = df.loc[df["Income Gap"].idxmax(), "Age"]
        ax.annotate(
            f"Largest Gap {compact_money_label(max_gap)}",
            xy=(max_gap_age, max_gap),
            xytext=(10, 18),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", alpha=0.5),
        )

    add_last_value_label(ax, ages, df["Total Spending"], f"Spending {compact_money_label(df['Total Spending'].iloc[-1])}")
    add_last_value_label(ax, ages, df["Guaranteed Income"], f"Guaranteed {compact_money_label(df['Guaranteed Income'].iloc[-1])}")

    ax.set_title("Income Gap and Guaranteed Income Coverage", fontsize=15, fontweight="bold", loc="left")
    ax.set_xlabel("Age")
    ax.set_ylabel("Annual Amount")
    style_axis_money(ax)
    ax.legend(loc="upper left", ncol=3, frameon=True)
    fig.tight_layout()
    return fig


def plot_withdrawal_rate_chart(df):
    fig, ax = plt.subplots(figsize=(12, 4.8))

    ages = df["Age"]
    wr = df["Withdrawal Rate"] * 100

    ax.bar(ages, wr, label="Withdrawal Rate %")
    ax.axhline(4, linestyle="--", linewidth=2, label="4% Reference")
    ax.axhline(6, linestyle="--", linewidth=2, label="6% Watch Zone")

    max_wr = wr.max()
    max_age = df.loc[wr.idxmax(), "Age"]
    ax.annotate(
        f"Max {max_wr:.1f}%",
        xy=(max_age, max_wr),
        xytext=(10, 14),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", alpha=0.5),
    )

    ax.set_title("Withdrawal Rate Pressure by Age", fontsize=15, fontweight="bold", loc="left")
    ax.set_xlabel("Age")
    ax.set_ylabel("Withdrawal Rate")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: f"{x:.0f}%"))
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    return fig



def run_projection_with_return_sequence(return_sequence):
    """
    Monte Carlo version of run_projection.
    Uses the same core logic, but replaces the fixed growth return with
    a year-by-year random return sequence.
    """
    if st.session_state.current_age <= 0 or st.session_state.retire_age <= 0 or st.session_state.end_age <= 0:
        return pd.DataFrame()

    rows = []
    trad = float(st.session_state.traditional)
    roth = float(st.session_state.roth)
    taxable = float(st.session_state.taxable)
    bucket1 = float(st.session_state.cash)
    base_spending = annual_household_spending()

    ages = list(range(int(st.session_state.current_age), int(st.session_state.end_age) + 1))

    for i, age in enumerate(ages):
        growth_return = float(return_sequence[i]) if i < len(return_sequence) else float(st.session_state.growth_return)

        year_offset = age - int(st.session_state.current_age)
        spouse_age = int(st.session_state.spouse_age) + year_offset if st.session_state.has_spouse else 0
        spouse_alive = bool(st.session_state.has_spouse and spouse_age <= int(st.session_state.spouse_plan_age))
        start_total = trad + roth + taxable + bucket1

        if age < int(st.session_state.retire_age):
            trad += float(st.session_state.annual_contribution) * 0.8
            roth += float(st.session_state.annual_contribution) * 0.2

        if spouse_alive and spouse_age < int(st.session_state.spouse_retire_age):
            trad += float(st.session_state.spouse_annual_contribution) * 0.8
            roth += float(st.session_state.spouse_annual_contribution) * 0.2

        trad *= (1 + growth_return)
        roth *= (1 + growth_return)
        taxable *= (1 + growth_return)
        bucket1 *= (1 + float(st.session_state.safe_return))

        household_retired = age >= int(st.session_state.retire_age) and (not spouse_alive or spouse_age >= int(st.session_state.spouse_retire_age))

        if household_retired and bucket1 <= 0 and base_spending > 0:
            target = annual_spending_for_age(age) * float(st.session_state.bucket1_years)
            transfer = min(trad, target)
            trad -= transfer
            bucket1 += transfer * 0.80

        conversion = 0
        if age >= int(st.session_state.retire_age) and float(st.session_state.annual_conversion) > 0:
            conversion = min(trad, float(st.session_state.annual_conversion))
            trad -= conversion
            roth += conversion

        user_ss = float(st.session_state.user_ss) if age >= int(st.session_state.user_ss_age) else 0
        spouse_ss = float(st.session_state.spouse_ss) if spouse_alive and spouse_age >= int(st.session_state.spouse_ss_age) else 0

        if st.session_state.has_spouse and not spouse_alive:
            if st.session_state.survivor_ss_strategy == "Higher benefit continues":
                ss_income = max(user_ss, float(st.session_state.spouse_ss))
            else:
                ss_income = user_ss
        else:
            ss_income = user_ss + spouse_ss

        inc = other_income_for_age(age, spouse_alive)
        other_income = inc["total"]
        guaranteed_income = ss_income + inc["guaranteed"]

        spending = 0
        if household_retired:
            years_retired = max(age - int(st.session_state.retire_age), 0)
            if st.session_state.has_spouse and not spouse_alive and float(st.session_state.survivor_spending) > 0:
                spending = float(st.session_state.survivor_spending) * ((1 + float(st.session_state.inflation)) ** years_retired)
            else:
                spending = annual_spending_for_age(age) * ((1 + float(st.session_state.inflation)) ** years_retired)

        healthcare = 0
        if age >= int(st.session_state.retire_age):
            healthcare += float(st.session_state.healthcare)
        if spouse_alive and spouse_age >= int(st.session_state.spouse_retire_age):
            healthcare += float(st.session_state.spouse_healthcare)

        total_spending = spending + healthcare
        non_portfolio_income = ss_income + other_income
        income_gap = max(total_spending - non_portfolio_income, 0)
        withdrawal_needed = income_gap

        used_b1 = used_taxable = used_trad = used_roth = 0.0

        take = min(bucket1, withdrawal_needed)
        bucket1 -= take
        withdrawal_needed -= take
        used_b1 += take

        take = min(taxable, withdrawal_needed)
        taxable -= take
        withdrawal_needed -= take
        used_taxable += take

        if withdrawal_needed > 0:
            gross_needed = withdrawal_needed / 0.80
            take = min(trad, gross_needed)
            trad -= take
            withdrawal_needed -= take * 0.80
            used_trad += take

        take = min(roth, max(withdrawal_needed, 0))
        roth -= take
        withdrawal_needed -= take
        used_roth += take

        actual_withdrawal = used_b1 + used_taxable + used_trad + used_roth
        end_total = trad + roth + taxable + bucket1

        rows.append({
            "Age": age,
            "Start Total": start_total,
            "End Total": end_total,
            "Total Spending": total_spending,
            "Total Non-Portfolio Income": non_portfolio_income,
            "Guaranteed Income": guaranteed_income,
            "Income Gap": income_gap,
            "Portfolio Withdrawal": actual_withdrawal,
            "Unmet Need": max(withdrawal_needed, 0),
            "Withdrawal Rate": actual_withdrawal / max(start_total, 1),
            "Income Coverage Ratio": non_portfolio_income / max(total_spending, 1),
            "Guaranteed Income Coverage Ratio": guaranteed_income / max(total_spending, 1),
            "Annual Return": growth_return,
        })

        if end_total <= 0 and withdrawal_needed > 0:
            break

    return pd.DataFrame(rows)


def run_monte_carlo_simulation(num_simulations, mean_return, volatility, seed=42):
    """
    Runs Monte Carlo simulations and returns summary + full result table.
    """
    rng = np.random.default_rng(seed)
    years = int(st.session_state.end_age) - int(st.session_state.current_age) + 1

    results = []
    paths = []

    for sim in range(num_simulations):
        returns = rng.normal(loc=mean_return, scale=volatility, size=years)
        returns = np.clip(returns, -0.45, 0.45)

        sim_df = run_projection_with_return_sequence(returns)

        if sim_df.empty:
            ending = 0
            success = False
            depletion_age = None
            max_wr = 0
        else:
            ending = float(sim_df["End Total"].iloc[-1])
            unmet = float(sim_df["Unmet Need"].sum())
            reached_end = int(sim_df["Age"].iloc[-1]) >= int(st.session_state.end_age)
            success = reached_end and ending > 0 and unmet <= 0

            depletion_age = None
            failed_rows = sim_df[(sim_df["End Total"] <= 0) | (sim_df["Unmet Need"] > 0)]
            if not failed_rows.empty:
                depletion_age = int(failed_rows["Age"].iloc[0])

            max_wr = float(sim_df["Withdrawal Rate"].max())

            paths.append(
                sim_df[["Age", "End Total"]]
                .assign(Simulation=sim)
            )

        results.append({
            "Simulation": sim + 1,
            "Success": success,
            "Ending Portfolio": ending,
            "Depletion Age": depletion_age,
            "Max Withdrawal Rate": max_wr,
            "Average Return": float(np.mean(returns)),
            "Worst Year Return": float(np.min(returns)),
        })

    results_df = pd.DataFrame(results)

    if paths:
        paths_df = pd.concat(paths, ignore_index=True)
    else:
        paths_df = pd.DataFrame(columns=["Age", "End Total", "Simulation"])

    success_rate = float(results_df["Success"].mean()) if not results_df.empty else 0
    median_ending = float(results_df["Ending Portfolio"].median()) if not results_df.empty else 0
    p10_ending = float(results_df["Ending Portfolio"].quantile(0.10)) if not results_df.empty else 0
    p90_ending = float(results_df["Ending Portfolio"].quantile(0.90)) if not results_df.empty else 0

    return {
        "success_rate": success_rate,
        "median_ending": median_ending,
        "p10_ending": p10_ending,
        "p90_ending": p90_ending,
        "results_df": results_df,
        "paths_df": paths_df,
    }


def plot_monte_carlo_paths(paths_df, results_df):
    fig, ax = plt.subplots(figsize=(12, 5.8))

    if paths_df.empty:
        ax.text(0.5, 0.5, "No simulation paths available", ha="center", va="center")
        return fig

    # Plot a limited sample for readability.
    sample_sims = paths_df["Simulation"].drop_duplicates().head(80)

    for sim in sample_sims:
        path = paths_df[paths_df["Simulation"] == sim]
        ax.plot(path["Age"], path["End Total"], linewidth=0.8, alpha=0.18)

    percentile_df = (
        paths_df.groupby("Age")["End Total"]
        .quantile([0.10, 0.50, 0.90])
        .unstack()
        .reset_index()
    )

    ax.plot(percentile_df["Age"], percentile_df[0.50], linewidth=3, label="Median Path")
    ax.plot(percentile_df["Age"], percentile_df[0.10], linewidth=2, linestyle="--", label="10th Percentile")
    ax.plot(percentile_df["Age"], percentile_df[0.90], linewidth=2, linestyle="--", label="90th Percentile")

    ax.axhline(0, linewidth=1)
    ax.set_title("Monte Carlo Portfolio Paths", fontsize=15, fontweight="bold", loc="left")
    ax.set_xlabel("Age")
    ax.set_ylabel("Portfolio Balance")
    style_axis_money(ax)
    ax.legend(loc="upper left", frameon=True)
    fig.tight_layout()
    return fig


def plot_monte_carlo_ending_distribution(results_df):
    fig, ax = plt.subplots(figsize=(12, 5.2))

    endings = results_df["Ending Portfolio"] if not results_df.empty else pd.Series(dtype=float)

    if endings.empty:
        ax.text(0.5, 0.5, "No simulation results available", ha="center", va="center")
        return fig

    ax.hist(endings, bins=30, alpha=0.85)
    ax.axvline(endings.median(), linewidth=3, label=f"Median {compact_money_label(endings.median())}")
    ax.axvline(endings.quantile(0.10), linewidth=2, linestyle="--", label=f"10th % {compact_money_label(endings.quantile(0.10))}")
    ax.axvline(endings.quantile(0.90), linewidth=2, linestyle="--", label=f"90th % {compact_money_label(endings.quantile(0.90))}")

    ax.set_title("Ending Portfolio Distribution", fontsize=15, fontweight="bold", loc="left")
    ax.set_xlabel("Ending Portfolio")
    ax.set_ylabel("Number of Simulations")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: compact_money_label(x)))
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    return fig



def run_stress_test_scenario(
    scenario_name,
    forced_returns=None,
    inflation_override=None,
    spending_multiplier=1.0,
):
    years = int(st.session_state.end_age) - int(st.session_state.current_age) + 1
    base_return = float(st.session_state.growth_return)

    if forced_returns is None:
        forced_returns = [base_return] * years
    else:
        forced_returns = list(forced_returns)
        if len(forced_returns) < years:
            forced_returns.extend([base_return] * (years - len(forced_returns)))

    original_inflation = float(st.session_state.inflation)
    original_spending = st.session_state.flat_monthly_spending

    try:
        if inflation_override is not None:
            st.session_state.inflation = inflation_override

        if st.session_state.budget_mode == "Flat monthly number":
            st.session_state.flat_monthly_spending = original_spending * spending_multiplier

        sim_df = run_projection_with_return_sequence(forced_returns)

    finally:
        st.session_state.inflation = original_inflation
        st.session_state.flat_monthly_spending = original_spending

    if sim_df.empty:
        return {
            "Scenario": scenario_name,
            "RTV Score": 0,
            "RTV Label": "Incomplete",
            "Result": "Failed",
            "Lasts Until Age": int(st.session_state.current_age),
            "Years Covered": 0,
            "Ending Portfolio": 0,
            "Max Withdrawal Rate": 0,
            "Income Coverage": 0,
        }

    rtv_score, rtv_label, _ = calculate_rtv_score(sim_df)

    ending = float(sim_df["End Total"].iloc[-1])
    max_wr = float(sim_df["Withdrawal Rate"].max())
    income_coverage = float(sim_df["Income Coverage Ratio"].mean())

    failed_rows = sim_df[(sim_df["End Total"] <= 0) | (sim_df["Unmet Need"] > 0)]

    if not failed_rows.empty:
        lasts_until_age = int(failed_rows["Age"].iloc[0])
    else:
        lasts_until_age = int(sim_df["Age"].iloc[-1])

    years_covered = max(lasts_until_age - int(st.session_state.current_age), 0)

    failed = (
        sim_df["Unmet Need"].sum() > 0
        or ending <= 0
        or int(sim_df["Age"].iloc[-1]) < int(st.session_state.end_age)
    )

    return {
        "Scenario": scenario_name,
        "RTV Score": rtv_score,
        "RTV Label": rtv_label,
        "Result": "Failed" if failed else "Survived",
        "Lasts Until Age": lasts_until_age,
        "Years Covered": years_covered,
        "Ending Portfolio": ending,
        "Max Withdrawal Rate": max_wr,
        "Income Coverage": income_coverage,
    }

def plot_stress_test_chart(stress_df):
    fig, ax = plt.subplots(figsize=(12, 5.5))

    bars = ax.bar(stress_df["Scenario"], stress_df["RTV Score"])

    for bar, score in zip(bars, stress_df["RTV Score"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            score + 1,
            f"{score}",
            ha="center",
            fontsize=10,
            fontweight="bold",
        )

    ax.axhline(75, linestyle="--", linewidth=2, label="Likely Viable")
    ax.axhline(90, linestyle="--", linewidth=2, label="Very Strong")

    ax.set_ylim(0, 105)
    ax.set_ylabel("RTV Score")
    ax.set_title("Stress Test RTV Scores", fontsize=15, fontweight="bold", loc="left")
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend()

    fig.tight_layout()
    return fig



def fig_to_reportlab_image(fig, width=6.8 * inch, height=3.6 * inch):
    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    img_buffer.seek(0)
    return Image(img_buffer, width=width, height=height)


def make_pdf_table(rows, col_widths=None, header=True):
    table = Table(rows, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ])

    table.setStyle(TableStyle(style))
    return table


def build_action_plan_rows(df, rtv_score):
    actions = build_rtv_improvement_recommendations(df, rtv_score)
    top = [a for a in actions if a["RTV Impact"] > 0][:7]

    rows = [["Possible Recommendation", "Why It May Help", "RTV Impact", "New RTV"]]

    if not top:
        rows.append([
            "Maintain current plan and monitor annually",
            "The current plan already appears strong under the current assumptions.",
            "0",
            str(rtv_score),
        ])
    else:
        for a in top:
            action = a["Action"]

            if "Reduce spending" in action:
                why = "Lowers portfolio withdrawals and reduces sequence-of-return pressure."
            elif "Delay retirement" in action:
                why = "Adds more saving years and shortens the withdrawal period."
            elif "contributions" in action:
                why = "Builds a larger portfolio before retirement begins."
            elif "Social Security" in action:
                why = "May increase guaranteed income and reduce portfolio withdrawals later."
            elif "Plan to age" in action:
                why = "Shortens the modeled planning horizon, but reduces longevity protection."
            else:
                why = "Improves one or more plan assumptions in the projection."

            rows.append([
                action,
                why,
                f"+{a['RTV Impact']}" if a["RTV Impact"] > 0 else str(a["RTV Impact"]),
                str(a["New RTV"]),
            ])

    return rows


def build_general_recommendation_paragraphs(df, rtv_score):
    ending = float(df["End Total"].iloc[-1])
    starting = float(df["Start Total"].iloc[0])
    max_wr = float(df["Withdrawal Rate"].max())
    avg_wr = float(df["Withdrawal Rate"].mean())
    income_coverage = float(df["Income Coverage Ratio"].mean())
    unmet_need = float(df["Unmet Need"].sum())

    recs = []

    if unmet_need > 0:
        recs.append("Address unmet spending needs first. This may require reducing spending, retiring later, increasing income, or increasing savings before retirement.")

    if max_wr > 0.07:
        recs.append("Review early-retirement spending. The plan shows a high maximum withdrawal rate, which can increase sequence-of-return risk.")
    elif max_wr > 0.05:
        recs.append("Monitor withdrawal pressure. A larger Bucket 1 or slightly lower spending could improve resilience.")
    else:
        recs.append("Withdrawal pressure appears reasonable under the current assumptions.")

    if income_coverage < 0.35:
        recs.append("Consider ways to increase dependable income, such as Social Security timing, part-time work, pension optimization, or other reliable income sources.")
    elif income_coverage >= 0.60:
        recs.append("Income coverage is a strength. Non-portfolio income is helping reduce reliance on investment withdrawals.")

    if ending > starting:
        recs.append("The ending portfolio is higher than the starting portfolio. This may suggest room for additional lifestyle spending, gifting, Roth conversion planning, or legacy planning.")
    elif ending > 500000:
        recs.append("The plan leaves a meaningful ending cushion, but should still be stress-tested for inflation, healthcare, and market timing.")
    else:
        recs.append("The ending cushion is limited. Protecting spending flexibility and reducing downside risk should be priorities.")

    if float(st.session_state.traditional or 0) > max(float(st.session_state.roth or 0) * 3, 250000):
        recs.append("Traditional retirement balances are much larger than Roth balances. Roth conversion planning may help manage future tax risk, especially before RMDs.")

    if int(st.session_state.retire_age or 0) < 65:
        recs.append("Because retirement is before Medicare age, healthcare costs and ACA subsidy planning should be reviewed carefully.")

    recs.append("Revisit the plan at least annually or after major life changes such as job changes, market changes, Social Security decisions, healthcare changes, or relocation.")

    return recs

def build_pdf_report(df):
    """
    Builds a polished PDF retirement report and returns bytes.
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#111827"),
        spaceAfter=10,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=14,
    )

    h1 = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#111827"),
        spaceBefore=14,
        spaceAfter=8,
    )

    h2 = ParagraphStyle(
        "SmallHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1f2937"),
        spaceBefore=8,
        spaceAfter=6,
    )

    body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#374151"),
        spaceAfter=7,
    )

    small = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#6b7280"),
    )

    story = []

    rtv_score, rtv_label, rtv_reasons = calculate_rtv_score(df)
    ending = float(df["End Total"].iloc[-1])
    starting = float(df["Start Total"].iloc[0])
    max_wr = float(df["Withdrawal Rate"].max())
    avg_income_coverage = float(df["Income Coverage Ratio"].mean())
    total_spending = float(df["Total Spending"].sum())
    total_withdrawals = float(df["Portfolio Withdrawal"].sum())

    # Cover
    story.append(Paragraph("Retirement Readiness Report", title_style))
    story.append(Paragraph(
        "A personalized planning report based on the current assumptions entered in the Retirement Decision Engine.",
        subtitle_style
    ))

    plan_type = "Couple / household plan" if st.session_state.has_spouse else "Individual plan"

    score_color = "#16a34a" if rtv_score >= 80 else ("#f59e0b" if rtv_score >= 60 else "#dc2626")

    summary_rows = [
        [
            Paragraph(f"<b><font color='{score_color}'>{rtv_score}/100</font></b><br/>RTV Score", body),
            Paragraph(f"<b>{rtv_label}</b><br/>RTV Label", body),
            Paragraph(f"<b>{money(ending)}</b><br/>End of Plan Portfolio", body),
            Paragraph(f"<b>{pct(max_wr)}</b><br/>Max Withdrawal Rate", body),
        ],
        [
            Paragraph(f"<b>{plan_type}</b><br/>Plan Type", body),
            Paragraph(f"<b>{st.session_state.current_age}</b><br/>Current Age", body),
            Paragraph(f"<b>{st.session_state.retire_age}</b><br/>Retirement Age", body),
            Paragraph(f"<b>{st.session_state.end_age}</b><br/>Plan Through Age", body),
        ],
    ]

    card_table = Table(summary_rows, colWidths=[1.7 * inch] * 4)
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#dbeafe")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 0.14 * inch))

    story.append(Paragraph("Executive Summary", h1))

    summary_text = (
        f"The current projection starts with {money(starting)} and ends with {money(ending)} "
        f"at age {int(st.session_state.end_age)}. The RTV score is {rtv_score}/100 ({rtv_label}). "
        f"The plan's highest projected withdrawal rate is {pct(max_wr)}, and average non-portfolio income "
        f"coverage is {pct(avg_income_coverage)}."
    )
    story.append(Paragraph(summary_text, body))

    if rtv_reasons:
        story.append(Paragraph("Main score drivers:", h2))
        for reason in rtv_reasons[:5]:
            story.append(Paragraph(f"- {reason}", body))

    story.append(Paragraph("<b>Educational purposes only:</b> This report is for general education and planning discussion only. It is not financial, tax, legal, insurance, or investment advice. Users should verify assumptions and consult qualified professionals before making retirement, tax, insurance, or investment decisions.", small))
    story.append(PageBreak())

    # Assumptions
    story.append(Paragraph("Plan Assumptions", h1))

    assumptions_rows = [
        ["Input", "Value"],
        ["Current Age", str(st.session_state.current_age)],
        ["Retirement Age", str(st.session_state.retire_age)],
        ["Plan Through Age", str(st.session_state.end_age)],
        ["Plan Type", plan_type],
        ["Traditional / Pre-tax", money(st.session_state.traditional)],
        ["Roth", money(st.session_state.roth)],
        ["Taxable", money(st.session_state.taxable)],
        ["Bucket 1 / Cash", money(st.session_state.cash)],
        ["Annual Contributions", money(st.session_state.annual_contribution)],
        ["Annual Spending Before Healthcare", money(annual_household_spending())],
        ["Annual Healthcare", money(st.session_state.healthcare)],
        ["Social Security Start Age", str(st.session_state.user_ss_age)],
        ["Annual Social Security", money(st.session_state.user_ss)],
        ["Growth Return", pct(st.session_state.growth_return)],
        ["Safe Return", pct(st.session_state.safe_return)],
        ["Inflation", pct(st.session_state.inflation)],
        ["Annual Roth Conversion", money(st.session_state.annual_conversion)],
        ["Bucket 1 Target Years", str(st.session_state.bucket1_years)],
    ]

    if st.session_state.has_spouse:
        assumptions_rows.extend([
            ["Spouse Age", str(st.session_state.spouse_age)],
            ["Spouse Retirement Age", str(st.session_state.spouse_retire_age)],
            ["Spouse Annual Social Security", money(st.session_state.spouse_ss)],
            ["Spouse Annual Healthcare", money(st.session_state.spouse_healthcare)],
        ])

    story.append(make_pdf_table(assumptions_rows, col_widths=[3.1 * inch, 3.1 * inch]))
    story.append(PageBreak())

    # Charts
    story.append(Paragraph("Dashboard Charts", h1))
    story.append(Paragraph("Portfolio balance by account type", h2))
    story.append(fig_to_reportlab_image(plot_portfolio_area_chart(df)))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Spending, income, and portfolio withdrawals", h2))
    story.append(fig_to_reportlab_image(plot_spending_income_bar_chart(df)))
    story.append(PageBreak())

    story.append(Paragraph("Income gap and withdrawal pressure", h1))
    story.append(Paragraph("Income gap", h2))
    story.append(fig_to_reportlab_image(plot_income_gap_chart(df)))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Withdrawal rate pressure", h2))
    story.append(fig_to_reportlab_image(plot_withdrawal_rate_chart(df)))
    story.append(PageBreak())

    # Recommendations
    story.append(Paragraph("Possible Recommendations", h1))
    story.append(Paragraph(
        "The ideas below are educational planning suggestions generated from the projection assumptions. "
        "They are not personalized financial advice. They are intended to help the user identify what to review, test, or discuss with a qualified professional.",
        body
    ))

    story.append(Paragraph("Planning Observations", h2))
    for rec in build_general_recommendation_paragraphs(df, rtv_score):
        story.append(Paragraph(f"- {rec}", body))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("RTV Improvement Ideas", h2))
    action_rows = build_action_plan_rows(df, rtv_score)
    story.append(make_pdf_table(action_rows, col_widths=[2.3 * inch, 2.6 * inch, 0.9 * inch, 0.8 * inch]))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Can the user spend more?", h2))

    spend_more_rows = build_spend_more_tests(rtv_score)
    spend_rows = [["Scenario", "New Monthly Spending", "New RTV", "Ending Portfolio"]]
    for row in spend_more_rows:
        spend_rows.append([
            row["Scenario"],
            money(row["New Monthly Spending"]),
            str(row["New RTV"]),
            money(row["Ending Portfolio"]),
        ])
    story.append(make_pdf_table(spend_rows, col_widths=[2.2 * inch, 1.7 * inch, 1.2 * inch, 1.8 * inch]))
    story.append(PageBreak())

    # Monte Carlo
    story.append(Paragraph("Monte Carlo Summary", h1))
    if "mc_result" in st.session_state:
        mc = st.session_state.mc_result
        mc_rows = [
            ["Metric", "Value"],
            ["Probability of Success", pct(mc["success_rate"])],
            ["Median Ending Portfolio", money(mc["median_ending"])],
            ["10th Percentile Ending", money(mc["p10_ending"])],
            ["90th Percentile Ending", money(mc["p90_ending"])],
        ]
        story.append(make_pdf_table(mc_rows, col_widths=[3.1 * inch, 3.1 * inch]))
        story.append(Spacer(1, 0.15 * inch))
        story.append(fig_to_reportlab_image(plot_monte_carlo_paths(mc["paths_df"], mc["results_df"])))
    else:
        story.append(Paragraph("Monte Carlo has not been run yet. Run the Monte Carlo page before exporting if you want this section populated.", body))

    story.append(PageBreak())

    # Stress Tests
    story.append(Paragraph("Stress Test Summary", h1))
    if "stress_results_df" in st.session_state:
        stress_df = st.session_state.stress_results_df.copy()
        stress_rows = [["Scenario", "RTV", "Result", "Lasts Until", "Ending Portfolio"]]

        for _, row in stress_df.iterrows():
            stress_rows.append([
                str(row.get("Scenario", "")),
                str(row.get("RTV Score", "")),
                str(row.get("Result", "")),
                str(row.get("Lasts Until Age", "")),
                money(row.get("Ending Portfolio", 0)),
            ])

        story.append(make_pdf_table(stress_rows, col_widths=[2.1 * inch, 0.7 * inch, 1.0 * inch, 1.2 * inch, 1.7 * inch]))
        story.append(Spacer(1, 0.15 * inch))
        story.append(fig_to_reportlab_image(plot_stress_test_chart(stress_df)))
    else:
        story.append(Paragraph("Stress tests have not been run yet. Run the Stress Tests page before exporting if you want this section populated.", body))

    story.append(PageBreak())

    # Projection snapshot
    story.append(Paragraph("Projection Snapshot", h1))
    projection_cols = [
        "Age", "End Total", "Total Spending", "Social Security",
        "Total Other Income", "Portfolio Withdrawal", "Withdrawal Rate"
    ]
    available_cols = [c for c in projection_cols if c in df.columns]
    snap = df[available_cols].copy()

    # Show every 5 years plus first/last
    snap = snap[(snap["Age"] % 5 == 0) | (snap["Age"] == df["Age"].iloc[0]) | (snap["Age"] == df["Age"].iloc[-1])]

    rows = [available_cols]
    for _, row in snap.iterrows():
        out_row = []
        for col in available_cols:
            if col == "Age":
                out_row.append(str(int(row[col])))
            elif col == "Withdrawal Rate":
                out_row.append(pct(row[col]))
            else:
                out_row.append(money(row[col]))
        rows.append(out_row)

    story.append(make_pdf_table(rows, col_widths=[0.55 * inch, 1.15 * inch, 1.1 * inch, 1.05 * inch, 1.15 * inch, 1.15 * inch, 0.85 * inch]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(0.55 * inch, 0.32 * inch, "Retirement Decision Engine - Educational Planning Report")
        canvas.drawRightString(7.95 * inch, 0.32 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    buffer.seek(0)
    return buffer.getvalue()



def build_saved_scenario_ai_context(name, summary, recommendations):
    return f"""
Saved scenario name: {name}

Key numbers:
- RTV score: {summary.get('score')}/100
- RTV label: {summary.get('label')}
- Current age: {summary.get('current_age')}
- Retirement age: {summary.get('retire_age')}
- Plan-through age: {summary.get('end_age')}
- Years to retirement: {summary.get('years_to_retire')}
- Total assets: {summary.get('total_assets')}
- Traditional/pre-tax assets: {summary.get('traditional')}
- Roth assets: {summary.get('roth')}
- Taxable assets: {summary.get('taxable')}
- Cash/Bucket 1: {summary.get('cash')}
- Monthly spending: {summary.get('monthly_spending')}
- Annual spending: {summary.get('annual_spending')}
- Annual income: {summary.get('annual_income')}
- Income coverage ratio: {summary.get('income_coverage')}
- Max withdrawal rate: {summary.get('rough_wr')}
- Growth return assumption: {summary.get('growth_return')}
- Safe return assumption: {summary.get('safe_return')}
- Inflation assumption: {summary.get('inflation')}
- Bucket 1 years: {summary.get('bucket1_years')}
- Annual Roth conversion: {summary.get('annual_conversion')}

Rule-based recommendations already identified:
{chr(10).join("- " + r for r in recommendations)}
"""


def generate_ai_recommendation_for_saved_scenario(name, summary, recommendations):
    """
    Uses OpenAI to generate a plain-English educational recommendation
    for one saved scenario.
    """
    try:
        from openai import OpenAI
        api_key = st.secrets.get("OPENAI_API_KEY", "")

        if not api_key:
            return "OpenAI API key is not configured. Add OPENAI_API_KEY in Streamlit Secrets to enable AI recommendations."

        client = OpenAI(api_key=api_key)

        prompt = f"""
You are an educational retirement planning assistant inside a retirement calculator.
You are not a financial advisor, CPA, attorney, insurance agent, or investment advisor.

Generate a concise, helpful recommendation for this saved retirement scenario.

Tone:
- Clear
- Friendly
- Practical
- No fearmongering
- No promises
- No personalized financial advice
- Educational only

Format:
1. Short overall read
2. Top 3 opportunities to improve the plan
3. Top 3 risks to review
4. One practical next step

Important:
- Explain using the scenario numbers.
- Do not invent missing information.
- Do not say the user should buy a specific product.
- Mention that this is educational only.

Scenario context:
{build_saved_scenario_ai_context(name, summary, recommendations)}
"""

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            max_output_tokens=700,
        )

        return response.output_text

    except Exception as e:
        return f"AI recommendation failed: {e}"



def get_phase1_retirement_places_data():
    """
    Phase 1 static scoring model.
    Scores are directional educational estimates on a 0-100 scale.
    They are intended for comparison, not tax advice.
    """
    return pd.DataFrame([
        {
            "State": "Florida",
            "Example Places": "Sarasota; The Villages; Naples; St. Augustine",
            "Tax Score": 96,
            "Cost Score": 68,
            "Healthcare Score": 82,
            "Lifestyle Score": 92,
            "Climate Score": 90,
            "Overall Score": 86,
            "Why It Ranks Well": "No state income tax; strong retiree infrastructure; warm weather; many coastal and golf communities.",
            "Watch Outs": "Higher homeowners insurance in some areas; hurricane risk; popular areas can be expensive.",
            "Best Fit": "Warm-weather retirees, golfers, beach lifestyle, no-income-tax preference",
        },
        {
            "State": "Tennessee",
            "Example Places": "Knoxville; Chattanooga; Franklin; Tellico Village",
            "Tax Score": 94,
            "Cost Score": 82,
            "Healthcare Score": 76,
            "Lifestyle Score": 78,
            "Climate Score": 74,
            "Overall Score": 83,
            "Why It Ranks Well": "No state income tax; relatively affordable; mild climate; good mix of mountains, lakes, and cities.",
            "Watch Outs": "Some popular areas have rising housing costs; summers can be hot and humid.",
            "Best Fit": "Low-tax living, mountain/lake lifestyle, moderate cost of living",
        },
        {
            "State": "South Carolina",
            "Example Places": "Hilton Head; Greenville; Charleston suburbs; Myrtle Beach",
            "Tax Score": 84,
            "Cost Score": 77,
            "Healthcare Score": 76,
            "Lifestyle Score": 90,
            "Climate Score": 84,
            "Overall Score": 82,
            "Why It Ranks Well": "Retirement-friendly tax treatment; strong golf/beach lifestyle; lower cost than many coastal states.",
            "Watch Outs": "Coastal insurance and hurricane exposure; Charleston/Hilton Head can be pricey.",
            "Best Fit": "Golfers, coastal retirees, snowbirds, warm-weather lifestyle",
        },
        {
            "State": "Arizona",
            "Example Places": "Scottsdale; Tucson; Mesa; Prescott",
            "Tax Score": 80,
            "Cost Score": 73,
            "Healthcare Score": 80,
            "Lifestyle Score": 86,
            "Climate Score": 82,
            "Overall Score": 80,
            "Why It Ranks Well": "Popular retiree destination; dry climate; strong healthcare access around Phoenix and Tucson.",
            "Watch Outs": "Extreme summer heat; water concerns; some markets have become expensive.",
            "Best Fit": "Dry-climate retirees, golfers, desert lifestyle, active adult communities",
        },
        {
            "State": "North Carolina",
            "Example Places": "Asheville; Raleigh suburbs; Wilmington; Pinehurst",
            "Tax Score": 76,
            "Cost Score": 75,
            "Healthcare Score": 82,
            "Lifestyle Score": 86,
            "Climate Score": 78,
            "Overall Score": 79,
            "Why It Ranks Well": "Strong healthcare corridors; mountains and beaches; moderate climate; good quality of life.",
            "Watch Outs": "State income tax applies; popular areas can be expensive.",
            "Best Fit": "Balanced lifestyle, healthcare access, mountains/beaches, golf",
        },
        {
            "State": "Texas",
            "Example Places": "San Antonio; Georgetown; Frisco; McAllen",
            "Tax Score": 94,
            "Cost Score": 73,
            "Healthcare Score": 79,
            "Lifestyle Score": 76,
            "Climate Score": 70,
            "Overall Score": 79,
            "Why It Ranks Well": "No state income tax; many affordable cities; strong healthcare in major metros.",
            "Watch Outs": "Property taxes can be high; hot summers; large driving distances.",
            "Best Fit": "No-income-tax preference, large metro healthcare, affordable city options",
        },
        {
            "State": "Georgia",
            "Example Places": "Savannah; Athens; Peachtree City; Blue Ridge",
            "Tax Score": 79,
            "Cost Score": 78,
            "Healthcare Score": 76,
            "Lifestyle Score": 80,
            "Climate Score": 80,
            "Overall Score": 78,
            "Why It Ranks Well": "Moderate cost; warm climate; good access to Atlanta healthcare; varied city/coastal/mountain options.",
            "Watch Outs": "Atlanta traffic; summer humidity; tax details vary by income type.",
            "Best Fit": "Warm climate, southern lifestyle, moderate affordability",
        },
        {
            "State": "Nevada",
            "Example Places": "Henderson; Reno; Mesquite; Summerlin",
            "Tax Score": 95,
            "Cost Score": 69,
            "Healthcare Score": 72,
            "Lifestyle Score": 78,
            "Climate Score": 78,
            "Overall Score": 77,
            "Why It Ranks Well": "No state income tax; dry climate; good retiree communities near Las Vegas and Reno.",
            "Watch Outs": "Healthcare access varies outside major metros; heat in southern Nevada; housing costs rose in popular areas.",
            "Best Fit": "No-income-tax preference, dry climate, entertainment access",
        },
        {
            "State": "Michigan",
            "Example Places": "Traverse City; Grand Rapids; Ann Arbor; Plymouth/Canton",
            "Tax Score": 67,
            "Cost Score": 74,
            "Healthcare Score": 84,
            "Lifestyle Score": 70,
            "Climate Score": 55,
            "Overall Score": 70,
            "Why It Ranks Well": "Strong healthcare in major metros; relatively affordable housing in many areas; excellent summer lifestyle.",
            "Watch Outs": "Cold winters; state tax planning matters; snowbird strategy may be attractive.",
            "Best Fit": "People keeping family ties, lower housing than coastal states, summer lifestyle",
        },
        {
            "State": "California",
            "Example Places": "San Diego; Palm Springs; San Luis Obispo; Sacramento suburbs",
            "Tax Score": 42,
            "Cost Score": 35,
            "Healthcare Score": 90,
            "Lifestyle Score": 95,
            "Climate Score": 92,
            "Overall Score": 68,
            "Why It Ranks Well": "Excellent climate and healthcare; strong lifestyle options; beaches, mountains, and culture.",
            "Watch Outs": "High cost of living; high taxes; housing affordability challenges.",
            "Best Fit": "High-budget retirees prioritizing climate, healthcare, and lifestyle",
        },
    ])


def score_badge(score):
    if score >= 85:
        return "Excellent"
    if score >= 75:
        return "Strong"
    if score >= 65:
        return "Moderate"
    return "High Cost / Specialized Fit"


def filter_places_data(df, priority):
    if priority == "Lowest taxes":
        return df.sort_values(["Tax Score", "Overall Score"], ascending=False)
    if priority == "Lowest cost":
        return df.sort_values(["Cost Score", "Overall Score"], ascending=False)
    if priority == "Healthcare access":
        return df.sort_values(["Healthcare Score", "Overall Score"], ascending=False)
    if priority == "Lifestyle / weather":
        return df.sort_values(["Lifestyle Score", "Climate Score", "Overall Score"], ascending=False)
    return df.sort_values("Overall Score", ascending=False)


def plot_best_states_scores(df):
    fig, ax = plt.subplots(figsize=(12, 5.5))
    show = df.head(10).sort_values("Overall Score")
    ax.barh(show["State"], show["Overall Score"])
    for i, v in enumerate(show["Overall Score"]):
        ax.text(v + 1, i, f"{int(v)}", va="center", fontweight="bold")
    ax.set_xlim(0, 105)
    ax.set_xlabel("Overall Retirement Fit Score")
    ax.set_title("Top Retirement States - Phase 1 Score", fontsize=15, fontweight="bold", loc="left")
    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig



def estimate_state_income_tax_simple(state, taxable_income, social_security_income=0, retirement_income=0):
    """
    Simplified educational state income tax estimate.
    This is intentionally directional, not tax advice.
    """
    taxable_income = max(float(taxable_income or 0), 0)
    social_security_income = max(float(social_security_income or 0), 0)
    retirement_income = max(float(retirement_income or 0), 0)

    no_income_tax_states = ["Florida", "Tennessee", "Texas", "Nevada"]
    if state in no_income_tax_states:
        return 0

    if state == "Arizona":
        return taxable_income * 0.025

    if state == "North Carolina":
        return taxable_income * 0.0425

    if state == "Michigan":
        # Directional estimate: Michigan has retirement-income rules/exemptions that vary by birth year.
        adjusted = max(taxable_income - min(retirement_income, 40000), 0)
        return adjusted * 0.0425

    if state == "South Carolina":
        # Directional estimate: retirement deductions can be meaningful, especially for older retirees.
        adjusted = max(taxable_income - min(retirement_income, 30000), 0)
        return adjusted * 0.064

    if state == "Georgia":
        # Directional estimate: retirement exclusion can reduce taxable retirement income.
        adjusted = max(taxable_income - min(retirement_income, 65000), 0)
        return adjusted * 0.0549

    if state == "California":
        # Simplified progressive-style estimate.
        brackets = [
            (10000, 0.01),
            (25000, 0.02),
            (50000, 0.04),
            (75000, 0.06),
            (150000, 0.08),
            (float("inf"), 0.093),
        ]
        remaining = taxable_income
        last = 0
        tax = 0
        for limit, rate in brackets:
            amount = min(remaining, limit - last)
            if amount <= 0:
                break
            tax += amount * rate
            remaining -= amount
            last = limit
        return tax

    return taxable_income * 0.05


def get_state_property_tax_rate_simple(state):
    rates = {
        "Florida": 0.0082,
        "Tennessee": 0.0056,
        "South Carolina": 0.0057,
        "Arizona": 0.0063,
        "North Carolina": 0.0075,
        "Texas": 0.0160,
        "Georgia": 0.0083,
        "Nevada": 0.0053,
        "Michigan": 0.0138,
        "California": 0.0075,
    }
    return rates.get(state, 0.009)


def get_state_sales_tax_rate_simple(state):
    rates = {
        "Florida": 0.070,
        "Tennessee": 0.095,
        "South Carolina": 0.074,
        "Arizona": 0.084,
        "North Carolina": 0.070,
        "Texas": 0.082,
        "Georgia": 0.074,
        "Nevada": 0.082,
        "Michigan": 0.060,
        "California": 0.087,
    }
    return rates.get(state, 0.07)


def estimate_total_state_tax_burden(state, ss_income, pretax_withdrawals, pension_other_income, taxable_income, annual_spending, home_value):
    """
    Estimates annual state-level tax burden:
    - simplified state income tax
    - estimated property tax
    - estimated sales tax on taxable spending
    """
    retirement_income = float(pretax_withdrawals or 0) + float(pension_other_income or 0)
    income_tax_base = float(pretax_withdrawals or 0) + float(pension_other_income or 0) + float(taxable_income or 0)

    # Most states here do not tax Social Security in this simplified model.
    # Phase 3 can add detailed SS taxation by state and filing status.
    income_tax = estimate_state_income_tax_simple(
        state,
        income_tax_base,
        social_security_income=ss_income,
        retirement_income=retirement_income
    )

    property_tax = float(home_value or 0) * get_state_property_tax_rate_simple(state)

    # Sales tax estimate: assume 45% of spending is taxable consumption.
    taxable_sales_spending = float(annual_spending or 0) * 0.45
    sales_tax = taxable_sales_spending * get_state_sales_tax_rate_simple(state)

    total_tax = income_tax + property_tax + sales_tax

    return {
        "Estimated Income Tax": income_tax,
        "Estimated Property Tax": property_tax,
        "Estimated Sales Tax": sales_tax,
        "Estimated Total State/Local Tax": total_tax,
        "Effective State/Local Tax Rate": total_tax / max(
            float(ss_income or 0) + float(pretax_withdrawals or 0) + float(pension_other_income or 0) + float(taxable_income or 0),
            1
        ),
    }


def build_personalized_places_table(places_df, ss_income, pretax_withdrawals, pension_other_income, taxable_income, annual_spending, home_value):
    rows = []

    for _, row in places_df.iterrows():
        state = row["State"]

        tax = estimate_total_state_tax_burden(
            state,
            ss_income=ss_income,
            pretax_withdrawals=pretax_withdrawals,
            pension_other_income=pension_other_income,
            taxable_income=taxable_income,
            annual_spending=annual_spending,
            home_value=home_value,
        )

        # Lower estimated annual tax burden gets a higher personalized tax score.
        total_tax = tax["Estimated Total State/Local Tax"]
        tax_drag_score = max(0, min(100, 100 - (total_tax / 750)))

        personalized_score = (
            tax_drag_score * 0.35
            + float(row["Cost Score"]) * 0.20
            + float(row["Healthcare Score"]) * 0.20
            + float(row["Lifestyle Score"]) * 0.15
            + float(row["Climate Score"]) * 0.10
        )

        rows.append({
            "State": state,
            "Example Places": row["Example Places"],
            "Personalized Score": round(personalized_score),
            "Estimated Annual Tax": total_tax,
            "Income Tax": tax["Estimated Income Tax"],
            "Property Tax": tax["Estimated Property Tax"],
            "Sales Tax": tax["Estimated Sales Tax"],
            "Effective Tax Rate": tax["Effective State/Local Tax Rate"],
            "Cost Score": row["Cost Score"],
            "Healthcare Score": row["Healthcare Score"],
            "Lifestyle Score": row["Lifestyle Score"],
            "Climate Score": row["Climate Score"],
            "Best Fit": row["Best Fit"],
            "Watch Outs": row["Watch Outs"],
        })

    return pd.DataFrame(rows).sort_values("Personalized Score", ascending=False).reset_index(drop=True)


def plot_personalized_tax_burden(personal_df):
    fig, ax = plt.subplots(figsize=(12, 5.5))
    show = personal_df.head(10).sort_values("Estimated Annual Tax", ascending=True)
    bars = ax.barh(show["State"], show["Estimated Annual Tax"])

    for i, v in enumerate(show["Estimated Annual Tax"]):
        ax.text(v + max(show["Estimated Annual Tax"].max() * 0.01, 250), i, money(v), va="center", fontweight="bold")

    ax.set_xlabel("Estimated Annual State/Local Tax")
    ax.set_title("Estimated Annual Tax by State", fontsize=15, fontweight="bold", loc="left")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: compact_money_label(x)))
    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig



def get_phase3_city_places_data():
    """
    Phase 3 static city/place-level retirement fit model.
    Scores are directional educational estimates on a 0-100 scale.
    """
    return pd.DataFrame([
        {
            "State": "Florida",
            "Place": "Sarasota",
            "Type": "Coastal / Arts / Beach",
            "Overall City Score": 88,
            "Affordability": 62,
            "Healthcare": 86,
            "Lifestyle": 95,
            "Golf / Recreation": 90,
            "Climate": 90,
            "Why Retire Here": "Beach lifestyle, arts, restaurants, golf, strong retiree infrastructure.",
            "Watch Outs": "Housing and insurance can be expensive; hurricane exposure.",
        },
        {
            "State": "Florida",
            "Place": "The Villages",
            "Type": "Active Adult / Golf Cart Community",
            "Overall City Score": 86,
            "Affordability": 72,
            "Healthcare": 78,
            "Lifestyle": 92,
            "Golf / Recreation": 96,
            "Climate": 88,
            "Why Retire Here": "Highly social active-adult lifestyle, golf carts, clubs, recreation, and no state income tax.",
            "Watch Outs": "May feel too retirement-specific for some; summer heat and insurance considerations.",
        },
        {
            "State": "Florida",
            "Place": "St. Augustine",
            "Type": "Coastal / Historic",
            "Overall City Score": 82,
            "Affordability": 68,
            "Healthcare": 75,
            "Lifestyle": 90,
            "Golf / Recreation": 82,
            "Climate": 86,
            "Why Retire Here": "Historic coastal feel, beaches nearby, walkable areas, and strong lifestyle appeal.",
            "Watch Outs": "Tourism, coastal insurance, and some housing-cost pressure.",
        },
        {
            "State": "South Carolina",
            "Place": "Hilton Head",
            "Type": "Coastal / Golf",
            "Overall City Score": 87,
            "Affordability": 58,
            "Healthcare": 76,
            "Lifestyle": 96,
            "Golf / Recreation": 97,
            "Climate": 84,
            "Why Retire Here": "Premier golf, beaches, bike paths, restaurants, and resort-style retirement lifestyle.",
            "Watch Outs": "Higher housing cost; coastal insurance and storm exposure.",
        },
        {
            "State": "South Carolina",
            "Place": "Greenville",
            "Type": "Small City / Mountains Nearby",
            "Overall City Score": 83,
            "Affordability": 77,
            "Healthcare": 78,
            "Lifestyle": 84,
            "Golf / Recreation": 78,
            "Climate": 78,
            "Why Retire Here": "Vibrant downtown, lower cost than coastal areas, mountain access, and good quality of life.",
            "Watch Outs": "Not coastal; growth has increased housing demand.",
        },
        {
            "State": "South Carolina",
            "Place": "Myrtle Beach",
            "Type": "Coastal / Golf / Value",
            "Overall City Score": 80,
            "Affordability": 75,
            "Healthcare": 72,
            "Lifestyle": 86,
            "Golf / Recreation": 94,
            "Climate": 84,
            "Why Retire Here": "Affordable coastal golf lifestyle with many courses and entertainment options.",
            "Watch Outs": "Tourism, seasonal traffic, and coastal storm risk.",
        },
        {
            "State": "Tennessee",
            "Place": "Knoxville",
            "Type": "University City / Mountains",
            "Overall City Score": 84,
            "Affordability": 82,
            "Healthcare": 78,
            "Lifestyle": 80,
            "Golf / Recreation": 76,
            "Climate": 74,
            "Why Retire Here": "No state income tax, access to Smoky Mountains, college-town energy, and moderate cost.",
            "Watch Outs": "Humidity and rising demand in popular neighborhoods.",
        },
        {
            "State": "Tennessee",
            "Place": "Chattanooga",
            "Type": "River City / Outdoors",
            "Overall City Score": 82,
            "Affordability": 80,
            "Healthcare": 75,
            "Lifestyle": 82,
            "Golf / Recreation": 74,
            "Climate": 74,
            "Why Retire Here": "Scenic river/mountain setting, outdoor activities, and no state income tax.",
            "Watch Outs": "Healthcare depth is not the same as larger metros.",
        },
        {
            "State": "Arizona",
            "Place": "Scottsdale",
            "Type": "Desert / Golf / Luxury",
            "Overall City Score": 85,
            "Affordability": 50,
            "Healthcare": 84,
            "Lifestyle": 94,
            "Golf / Recreation": 98,
            "Climate": 78,
            "Why Retire Here": "World-class golf, healthcare access, dining, resorts, and active adult communities.",
            "Watch Outs": "Expensive housing and extreme summer heat.",
        },
        {
            "State": "Arizona",
            "Place": "Tucson",
            "Type": "Desert / University / Value",
            "Overall City Score": 81,
            "Affordability": 74,
            "Healthcare": 80,
            "Lifestyle": 80,
            "Golf / Recreation": 84,
            "Climate": 78,
            "Why Retire Here": "More affordable than Scottsdale, strong outdoor lifestyle, dry climate, and healthcare access.",
            "Watch Outs": "Summer heat and desert climate may not fit everyone.",
        },
        {
            "State": "North Carolina",
            "Place": "Pinehurst",
            "Type": "Golf / Village",
            "Overall City Score": 84,
            "Affordability": 72,
            "Healthcare": 76,
            "Lifestyle": 86,
            "Golf / Recreation": 98,
            "Climate": 78,
            "Why Retire Here": "One of the strongest golf-retirement fits in the country with a village feel.",
            "Watch Outs": "Smaller-town setting; not coastal or major metro.",
        },
        {
            "State": "North Carolina",
            "Place": "Wilmington",
            "Type": "Coastal / Small City",
            "Overall City Score": 82,
            "Affordability": 68,
            "Healthcare": 78,
            "Lifestyle": 90,
            "Golf / Recreation": 82,
            "Climate": 80,
            "Why Retire Here": "Coastal lifestyle, beaches, restaurants, and good regional healthcare.",
            "Watch Outs": "Hurricane exposure and rising housing costs.",
        },
        {
            "State": "Texas",
            "Place": "Georgetown",
            "Type": "Active Adult / Austin Area",
            "Overall City Score": 81,
            "Affordability": 70,
            "Healthcare": 78,
            "Lifestyle": 82,
            "Golf / Recreation": 82,
            "Climate": 70,
            "Why Retire Here": "Active-adult communities, no state income tax, and access to Austin-area healthcare.",
            "Watch Outs": "Property taxes and hot summers.",
        },
        {
            "State": "Nevada",
            "Place": "Henderson",
            "Type": "Desert / Las Vegas Area",
            "Overall City Score": 80,
            "Affordability": 66,
            "Healthcare": 76,
            "Lifestyle": 82,
            "Golf / Recreation": 84,
            "Climate": 76,
            "Why Retire Here": "No state income tax, entertainment access, golf, and airport convenience.",
            "Watch Outs": "Summer heat and healthcare varies by provider access.",
        },
        {
            "State": "Michigan",
            "Place": "Traverse City",
            "Type": "Lake / Summer Lifestyle",
            "Overall City Score": 76,
            "Affordability": 58,
            "Healthcare": 72,
            "Lifestyle": 88,
            "Golf / Recreation": 82,
            "Climate": 55,
            "Why Retire Here": "Beautiful lake lifestyle, wineries, golf, and excellent summers.",
            "Watch Outs": "Cold winters and housing can be expensive for Michigan.",
        },
        {
            "State": "Michigan",
            "Place": "Grand Rapids",
            "Type": "Mid-size City / Healthcare",
            "Overall City Score": 74,
            "Affordability": 73,
            "Healthcare": 84,
            "Lifestyle": 74,
            "Golf / Recreation": 72,
            "Climate": 54,
            "Why Retire Here": "Strong healthcare, reasonable cost, airport, restaurants, and West Michigan lifestyle.",
            "Watch Outs": "Winter weather and state tax planning.",
        },
    ])


def filter_city_places(city_df, selected_states, lifestyle_priority):
    df = city_df.copy()

    if selected_states:
        df = df[df["State"].isin(selected_states)]

    if lifestyle_priority == "Golf / recreation":
        df = df.sort_values(["Golf / Recreation", "Overall City Score"], ascending=False)
    elif lifestyle_priority == "Healthcare":
        df = df.sort_values(["Healthcare", "Overall City Score"], ascending=False)
    elif lifestyle_priority == "Lower cost":
        df = df.sort_values(["Affordability", "Overall City Score"], ascending=False)
    elif lifestyle_priority == "Coastal / warm lifestyle":
        df = df[df["Type"].str.contains("Coastal|Beach|Desert", case=False, regex=True)]
        df = df.sort_values(["Lifestyle", "Climate", "Overall City Score"], ascending=False)
    elif lifestyle_priority == "Active adult community":
        df = df[df["Type"].str.contains("Active Adult|Golf Cart", case=False, regex=True)]
        df = df.sort_values(["Lifestyle", "Golf / Recreation", "Overall City Score"], ascending=False)
    else:
        df = df.sort_values("Overall City Score", ascending=False)

    return df.reset_index(drop=True)


def plot_city_scores(city_df):
    fig, ax = plt.subplots(figsize=(12, 5.5))
    show = city_df.head(10).sort_values("Overall City Score")
    labels = show["Place"] + ", " + show["State"]
    ax.barh(labels, show["Overall City Score"])
    for i, v in enumerate(show["Overall City Score"]):
        ax.text(v + 1, i, f"{int(v)}", va="center", fontweight="bold")
    ax.set_xlim(0, 105)
    ax.set_xlabel("City Retirement Fit Score")
    ax.set_title("Top Places to Retire - Phase 3 City Scores", fontsize=15, fontweight="bold", loc="left")
    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig



def build_state_comparison_table(places_df, personal_df, selected_states):
    rows = []

    for state in selected_states:
        base = places_df[places_df["State"] == state]
        personal = personal_df[personal_df["State"] == state]

        if base.empty or personal.empty:
            continue

        b = base.iloc[0]
        p = personal.iloc[0]

        rows.append({
            "State": state,
            "Overall Score": b["Overall Score"],
            "Personalized Score": p["Personalized Score"],
            "Estimated Annual Tax": p["Estimated Annual Tax"],
            "Income Tax": p["Income Tax"],
            "Property Tax": p["Property Tax"],
            "Sales Tax": p["Sales Tax"],
            "Effective Tax Rate": p["Effective Tax Rate"],
            "Cost Score": b["Cost Score"],
            "Healthcare Score": b["Healthcare Score"],
            "Lifestyle Score": b["Lifestyle Score"],
            "Climate Score": b["Climate Score"],
            "Example Places": b["Example Places"],
            "Best Fit": b["Best Fit"],
            "Watch Outs": b["Watch Outs"],
        })

    return pd.DataFrame(rows)


def plot_state_comparison_scores(compare_df):
    fig, ax = plt.subplots(figsize=(12, 5.5))

    x = range(len(compare_df))
    width = 0.35

    ax.bar([i - width / 2 for i in x], compare_df["Overall Score"], width=width, label="Base Score")
    ax.bar([i + width / 2 for i in x], compare_df["Personalized Score"], width=width, label="Personalized Score")

    ax.set_xticks(list(x))
    ax.set_xticklabels(compare_df["State"])
    ax.set_ylim(0, 105)

    for i, row in compare_df.iterrows():
        ax.text(i - width / 2, row["Overall Score"] + 1, str(int(row["Overall Score"])), ha="center", fontweight="bold")
        ax.text(i + width / 2, row["Personalized Score"] + 1, str(int(row["Personalized Score"])), ha="center", fontweight="bold")

    ax.set_ylabel("Score")
    ax.set_title("Base vs Personalized Retirement Fit", fontsize=15, fontweight="bold", loc="left")
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_state_tax_stack(compare_df):
    fig, ax = plt.subplots(figsize=(12, 5.5))

    states = compare_df["State"]
    income_tax = compare_df["Income Tax"]
    property_tax = compare_df["Property Tax"]
    sales_tax = compare_df["Sales Tax"]

    ax.bar(states, income_tax, label="Income Tax")
    ax.bar(states, property_tax, bottom=income_tax, label="Property Tax")
    ax.bar(states, sales_tax, bottom=income_tax + property_tax, label="Sales Tax")

    totals = compare_df["Estimated Annual Tax"]
    for i, total in enumerate(totals):
        ax.text(i, total + max(totals.max() * 0.02, 250), money(total), ha="center", fontweight="bold")

    ax.set_ylabel("Estimated Annual Tax")
    ax.set_title("Estimated Tax Burden Breakdown", fontsize=15, fontweight="bold", loc="left")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: compact_money_label(x)))
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend()
    fig.tight_layout()
    return fig


def build_compare_narrative(compare_df):
    if compare_df.empty:
        return []

    best_score = compare_df.sort_values("Personalized Score", ascending=False).iloc[0]
    lowest_tax = compare_df.sort_values("Estimated Annual Tax").iloc[0]
    best_healthcare = compare_df.sort_values("Healthcare Score", ascending=False).iloc[0]
    best_lifestyle = compare_df.sort_values("Lifestyle Score", ascending=False).iloc[0]
    best_cost = compare_df.sort_values("Cost Score", ascending=False).iloc[0]

    notes = [
        f"Best overall personalized fit: **{best_score['State']}** with a personalized score of **{int(best_score['Personalized Score'])}/100**.",
        f"Lowest estimated annual tax burden: **{lowest_tax['State']}** at about **{money(lowest_tax['Estimated Annual Tax'])}** per year.",
        f"Best healthcare score: **{best_healthcare['State']}** with a healthcare score of **{int(best_healthcare['Healthcare Score'])}/100**.",
        f"Best lifestyle score: **{best_lifestyle['State']}** with a lifestyle score of **{int(best_lifestyle['Lifestyle Score'])}/100**.",
        f"Best cost score: **{best_cost['State']}** with a cost score of **{int(best_cost['Cost Score'])}/100**.",
    ]

    return notes



def calculate_location_fit_profile(
    tax_weight,
    cost_weight,
    healthcare_weight,
    lifestyle_weight,
    climate_weight,
    golf_weight,
):
    total = tax_weight + cost_weight + healthcare_weight + lifestyle_weight + climate_weight + golf_weight
    if total <= 0:
        total = 1

    return {
        "tax": tax_weight / total,
        "cost": cost_weight / total,
        "healthcare": healthcare_weight / total,
        "lifestyle": lifestyle_weight / total,
        "climate": climate_weight / total,
        "golf": golf_weight / total,
    }


def build_retirement_location_recommendation_engine(
    city_df,
    personal_df,
    weights,
    preferred_states=None,
    avoid_states=None,
    wants_snowbird=False,
):
    preferred_states = preferred_states or []
    avoid_states = avoid_states or []

    rows = []

    for _, city in city_df.iterrows():
        state = city["State"]

        if avoid_states and state in avoid_states:
            continue

        p = personal_df[personal_df["State"] == state]
        if p.empty:
            continue
        p = p.iloc[0]

        preference_bonus = 0
        if preferred_states and state in preferred_states:
            preference_bonus += 5

        snowbird_bonus = 0
        if wants_snowbird and city["Climate"] >= 80:
            snowbird_bonus += 4

        score = (
            (100 - min(float(p["Estimated Annual Tax"]) / 750, 100)) * weights["tax"]
            + float(city["Affordability"]) * weights["cost"]
            + float(city["Healthcare"]) * weights["healthcare"]
            + float(city["Lifestyle"]) * weights["lifestyle"]
            + float(city["Climate"]) * weights["climate"]
            + float(city["Golf / Recreation"]) * weights["golf"]
            + preference_bonus
            + snowbird_bonus
        )

        rows.append({
            "Place": city["Place"],
            "State": state,
            "Type": city["Type"],
            "Recommended Fit Score": round(min(score, 100)),
            "Estimated Annual State/Local Tax": p["Estimated Annual Tax"],
            "Healthcare": city["Healthcare"],
            "Affordability": city["Affordability"],
            "Lifestyle": city["Lifestyle"],
            "Climate": city["Climate"],
            "Golf / Recreation": city["Golf / Recreation"],
            "Why It Fits": city["Why Retire Here"],
            "Watch Outs": city["Watch Outs"],
        })

    return pd.DataFrame(rows).sort_values("Recommended Fit Score", ascending=False).reset_index(drop=True)


def build_snowbird_recommendations(location_df, current_home_state="Michigan"):
    warm_states = ["Florida", "South Carolina", "Arizona", "Texas", "Nevada", "Georgia"]
    snowbird_df = location_df[location_df["State"].isin(warm_states)].copy()

    if snowbird_df.empty:
        return pd.DataFrame()

    snowbird_df["Snowbird Fit Score"] = (
        snowbird_df["Climate"] * 0.30
        + snowbird_df["Lifestyle"] * 0.25
        + snowbird_df["Golf / Recreation"] * 0.25
        + snowbird_df["Healthcare"] * 0.10
        + snowbird_df["Affordability"] * 0.10
    ).round()

    snowbird_df["Snowbird Strategy"] = (
        "Keep primary home in " + current_home_state
        + " and spend winter months here before buying."
    )

    return snowbird_df.sort_values("Snowbird Fit Score", ascending=False).reset_index(drop=True)


def plot_location_engine_scores(location_df):
    fig, ax = plt.subplots(figsize=(12, 5.5))

    show = location_df.head(10).sort_values("Recommended Fit Score")
    labels = show["Place"] + ", " + show["State"]

    ax.barh(labels, show["Recommended Fit Score"])

    for i, v in enumerate(show["Recommended Fit Score"]):
        ax.text(v + 1, i, f"{int(v)}", va="center", fontweight="bold")

    ax.set_xlim(0, 105)
    ax.set_xlabel("Personalized Location Fit Score")
    ax.set_title("Personalized Retirement Location Recommendations", fontsize=15, fontweight="bold", loc="left")
    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def build_location_recommendation_summary(location_df):
    if location_df.empty:
        return []

    top = location_df.iloc[0]
    lowest_tax = location_df.sort_values("Estimated Annual State/Local Tax").iloc[0]
    best_healthcare = location_df.sort_values("Healthcare", ascending=False).iloc[0]
    best_golf = location_df.sort_values("Golf / Recreation", ascending=False).iloc[0]
    best_value = location_df.sort_values("Affordability", ascending=False).iloc[0]

    return [
        f"Best overall personalized match: **{top['Place']}, {top['State']}** with a fit score of **{int(top['Recommended Fit Score'])}/100**.",
        f"Lowest estimated tax option among recommendations: **{lowest_tax['Place']}, {lowest_tax['State']}** at about **{money(lowest_tax['Estimated Annual State/Local Tax'])}** per year.",
        f"Best healthcare score: **{best_healthcare['Place']}, {best_healthcare['State']}**.",
        f"Best golf/recreation score: **{best_golf['Place']}, {best_golf['State']}**.",
        f"Best affordability score: **{best_value['Place']}, {best_value['State']}**.",
    ]



def run_projection_with_temp_monthly_spending(test_monthly_spending):
    original_budget_mode = st.session_state.budget_mode
    original_flat_monthly_spending = st.session_state.flat_monthly_spending
    original_enable_spending_change = st.session_state.enable_spending_change

    try:
        st.session_state.budget_mode = "Flat monthly number"
        st.session_state.flat_monthly_spending = float(test_monthly_spending)
        st.session_state.enable_spending_change = False

        test_df = run_projection()
        if test_df is None or test_df.empty:
            return None, 0, "Incomplete"

        score_result = calculate_rtv_score(test_df)
        test_score = score_result[0]
        test_label = score_result[1]

        return test_df, test_score, test_label

    finally:
        st.session_state.budget_mode = original_budget_mode
        st.session_state.flat_monthly_spending = original_flat_monthly_spending
        st.session_state.enable_spending_change = original_enable_spending_change


def find_monthly_spending_for_target_score(target_score=80):
    current_monthly = annual_household_spending() / 12

    if current_monthly <= 0:
        return None

    # First check current result.
    current_test_df, current_score, current_label = run_projection_with_temp_monthly_spending(current_monthly)

    if current_test_df is None:
        return None

    # If current score is below target, search lower spending.
    if current_score < target_score:
        low = 0
        high = current_monthly
        best_monthly = None
        best_score = 0
        best_label = "Incomplete"

        for _ in range(24):
            mid = (low + high) / 2
            test_df, test_score, test_label = run_projection_with_temp_monthly_spending(mid)

            if test_df is None:
                high = mid
                continue

            if test_score >= target_score:
                best_monthly = mid
                best_score = test_score
                best_label = test_label
                low = mid
            else:
                high = mid

        return {
            "mode": "lower",
            "target_score": target_score,
            "current_monthly": current_monthly,
            "current_score": current_score,
            "current_label": current_label,
            "suggested_monthly": best_monthly,
            "suggested_score": best_score,
            "suggested_label": best_label,
            "monthly_difference": (best_monthly - current_monthly) if best_monthly is not None else None,
        }

    # If current score is healthy, search higher spending until target is almost lost.
    low = current_monthly
    high = current_monthly * 2.0

    # Expand high limit if plan is very strong.
    for _ in range(5):
        test_df, test_score, test_label = run_projection_with_temp_monthly_spending(high)
        if test_df is not None and test_score >= target_score:
            low = high
            high *= 1.5
        else:
            break

    best_monthly = current_monthly
    best_score = current_score
    best_label = current_label

    for _ in range(24):
        mid = (low + high) / 2
        test_df, test_score, test_label = run_projection_with_temp_monthly_spending(mid)

        if test_df is not None and test_score >= target_score:
            best_monthly = mid
            best_score = test_score
            best_label = test_label
            low = mid
        else:
            high = mid

    return {
        "mode": "higher",
        "target_score": target_score,
        "current_monthly": current_monthly,
        "current_score": current_score,
        "current_label": current_label,
        "suggested_monthly": best_monthly,
        "suggested_score": best_score,
        "suggested_label": best_label,
        "monthly_difference": best_monthly - current_monthly,
    }


# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs([
    "Home",
    "Guided Questions",
    "Budget Builder",
    "Income Builder",
    "Spouse Questions",
    "Review Answers",
    "Dashboard",
    "Recommendations",
    "Projection Table",
    "Saved Scenarios",
    "Best Places to Retire",
    "Monte Carlo",
    "Stress Tests",
    "PDF Report",
    "AI Retirement Coach",
    "Help / Instructions",
])


with tabs[0]:
    st.header("Home Dashboard")
    st.caption("A quick overview of your retirement plan setup, saved scenarios, and next best steps.")

    if user:
        st.success(f"Signed in as: {user.email}")
    else:
        st.warning("You are not signed in. You can still use the planner, but saved scenarios require an account.")

    missing_items_home = required_missing()

    safe_df_home = pd.DataFrame()
    safe_can_run_home = False

    try:
        if len(missing_items_home) == 0:
            safe_df_home = run_projection()
            safe_can_run_home = isinstance(safe_df_home, pd.DataFrame) and not safe_df_home.empty
    except Exception as e:
        safe_df_home = pd.DataFrame()
        safe_can_run_home = False
        st.warning(f"Projection cannot run yet: {e}")

    c1, c2, c3, c4 = st.columns(4)

    if safe_can_run_home:
        try:
            score_result_home = calculate_rtv_score(safe_df_home)
            rtv_score_home = score_result_home[0]
            rtv_label_home = score_result_home[1]
        except Exception:
            rtv_score_home = 0
            rtv_label_home = "Incomplete"

        c1.metric("RTV Score", f"{rtv_score_home}/100", rtv_label_home)
        c2.metric("Ending Portfolio", money(safe_df_home["End Total"].iloc[-1]))
        c3.metric("Max Withdrawal Rate", pct(safe_df_home["Withdrawal Rate"].max()))
        c4.metric("Income Coverage", pct(safe_df_home["Income Coverage Ratio"].mean()))

        st.success("Your plan has enough information to review the dashboard, recommendations, Monte Carlo, stress tests, and reports.")
    else:
        c1.metric("RTV Score", "Incomplete")
        c2.metric("Ending Portfolio", "$0")
        c3.metric("Max Withdrawal Rate", "0.0%")
        c4.metric("Income Coverage", "0.0%")

        if missing_items_home:
            st.warning("Complete these required items: " + ", ".join(missing_items_home))
        else:
            st.info("Your saved scenario loaded, but the projection needs review. Check Guided Questions and Budget Builder.")

    st.divider()

    st.subheader("Quick Start")
    st.write("""
1. Complete **Guided Questions**.
2. Add spending in **Budget Builder**.
3. Add other income in **Income Builder**.
4. Use **Dashboard** and **Recommendations**.
5. Save and compare scenarios in **Saved Scenarios**.
6. Run **Monte Carlo**, **Stress Tests**, and export a **PDF Report**.
""")

    st.caption("Educational planning tool only. Not financial, tax, legal, insurance, or investment advice.")


with tabs[1]:
    st.header("Guided Retirement Questions")
    page_help(
        "Guided Retirement Questions",
        "This page collects the core numbers for the retirement projection: ages, savings, contributions, Social Security, expected returns, inflation, Roth conversions, and Bucket 1 strategy. These inputs drive the Dashboard, RTV score, Recommendations, and Projection Table."
    )

    with st.form("guided_form"):
        st.subheader("Timeline")
        c1, c2, c3 = st.columns(3)
        current_age = c1.number_input("How old are you today?", 0, 100, st.session_state.current_age, help=FIELD_HELP["current_age"])
        retire_age = c2.number_input("What age do you want to retire?", 0, 100, st.session_state.retire_age, help=FIELD_HELP["retire_age"])
        end_age = c3.number_input("What age should the plan last until?", 0, 110, st.session_state.end_age, help=FIELD_HELP["end_age"])

        st.subheader("Savings")
        c1, c2, c3, c4 = st.columns(4)
        traditional = c1.number_input("Traditional 401k/IRA total", min_value=0, value=st.session_state.traditional, step=10000, help=FIELD_HELP["traditional"])
        roth = c2.number_input("Roth total", min_value=0, value=st.session_state.roth, step=10000, help=FIELD_HELP["roth"])
        taxable = c3.number_input("Taxable brokerage", min_value=0, value=st.session_state.taxable, step=10000, help=FIELD_HELP["taxable"])
        cash = c4.number_input("Bucket 1 / cash / safe money", min_value=0, value=st.session_state.cash, step=10000, help=FIELD_HELP["cash"])

        st.subheader("Contributions, healthcare, Social Security")
        c1, c2, c3, c4 = st.columns(4)
        annual_contribution = c1.number_input("Annual contributions until retirement", min_value=0, value=st.session_state.annual_contribution, step=5000, help=FIELD_HELP["annual_contribution"])
        healthcare = c2.number_input("Your annual healthcare in retirement", min_value=0, value=st.session_state.healthcare, step=1000, help=FIELD_HELP["healthcare"])
        user_ss_age = c3.number_input("Your Social Security start age", 62, 70, st.session_state.user_ss_age, help=FIELD_HELP["user_ss_age"])
        user_ss = c4.number_input("Your annual Social Security", min_value=0, value=st.session_state.user_ss, step=1000, help=FIELD_HELP["user_ss"])

        st.subheader("Assumptions")
        c1, c2, c3 = st.columns(3)
        growth_return = c1.slider("Growth return", 0.0, 15.0, st.session_state.growth_return * 100, help=FIELD_HELP["growth_return"]) / 100
        safe_return = c2.slider("Bucket 1 safe return", 0.0, 10.0, st.session_state.safe_return * 100, help=FIELD_HELP["safe_return"]) / 100
        inflation = c3.slider("Inflation", 0.0, 10.0, st.session_state.inflation * 100, help=FIELD_HELP["inflation"]) / 100

        st.subheader("Strategy")
        c1, c2 = st.columns(2)
        annual_conversion = c1.number_input("Annual Roth conversion to test", min_value=0, value=int(st.session_state.annual_conversion), step=5000, help=FIELD_HELP["annual_conversion"])
        bucket1_years = c2.number_input("Bucket 1 target years of spending", min_value=0.0, max_value=10.0, value=float(st.session_state.bucket1_years), step=0.5, help=FIELD_HELP["bucket1_years"])

        if st.session_state.enable_spending_change and int(st.session_state.spending_change_age or 0) > 0:
            st.subheader("Planned Spending Change")
            s1, s2 = st.columns(2)
            s1.metric("Spending Change Age", int(st.session_state.spending_change_age))
            s2.metric("New Monthly Spending", money(st.session_state.spending_change_monthly))
            st.info("The projection uses this new spending amount starting at the selected age, then continues applying inflation.")

        st.subheader("Home & Housing Strategy")
        st.caption("Optional, but useful. Your home can affect retirement flexibility, mortgage cash flow, downsizing options, taxes, and relocation decisions.")

        c1, c2, c3 = st.columns(3)
        home_value = c1.number_input("Current home value", min_value=0, value=int(st.session_state.home_value), step=10000, help="Estimated current market value of your primary home.")
        mortgage_balance = c2.number_input("Remaining mortgage balance", min_value=0, value=int(st.session_state.mortgage_balance), step=5000, help="How much you still owe on the home.")
        monthly_mortgage = c3.number_input("Monthly mortgage payment", min_value=0, value=int(st.session_state.monthly_mortgage), step=100, help="Principal and interest payment. If taxes and insurance are escrowed, you can include the full payment here.")

        c1, c2, c3 = st.columns(3)
        annual_property_taxes_home = c1.number_input("Annual property taxes", min_value=0, value=int(st.session_state.annual_property_taxes_home), step=500, help="Estimated yearly property tax bill for the home.")
        mortgage_payoff_age = c2.number_input("Mortgage payoff age", min_value=0, max_value=110, value=int(st.session_state.mortgage_payoff_age), step=1, help="Age when the mortgage is expected to be paid off. Use 0 if unknown.")
        retirement_housing_plan = c3.selectbox(
            "Retirement housing plan",
            ["Stay in Current Home", "Downsize", "Relocate", "Snowbird", "Unsure"],
            index=["Stay in Current Home", "Downsize", "Relocate", "Snowbird", "Unsure"].index(st.session_state.retirement_housing_plan) if st.session_state.retirement_housing_plan in ["Stay in Current Home", "Downsize", "Relocate", "Snowbird", "Unsure"] else 4,
            help="How you expect housing to change in retirement."
        )

        st.info(f"Estimated home equity: {money(max(home_value - mortgage_balance, 0))}")

        save = st.form_submit_button("Save main answers")

    if save:
        for k, v in {
            "current_age": current_age, "retire_age": retire_age, "end_age": end_age,
            "traditional": traditional, "roth": roth, "taxable": taxable, "cash": cash,
            "annual_contribution": annual_contribution, "healthcare": healthcare,
            "user_ss_age": user_ss_age, "user_ss": user_ss,
            "growth_return": growth_return, "safe_return": safe_return, "inflation": inflation,
            "annual_conversion": annual_conversion, "bucket1_years": bucket1_years,
            "home_value": home_value,
            "mortgage_balance": mortgage_balance,
            "monthly_mortgage": monthly_mortgage,
            "annual_property_taxes_home": annual_property_taxes_home,
            "mortgage_payoff_age": mortgage_payoff_age,
            "retirement_housing_plan": retirement_housing_plan,
        }.items():
            st.session_state[k] = v
        st.success("Main answers saved.")

with tabs[2]:
    st.header("Household Spending / Budget Builder")
    page_help(
        "Budget Builder",
        "This page estimates how much money you need each year in retirement. You can use a simple flat monthly amount or enter a detailed monthly budget. Healthcare is handled separately so the app can model it more clearly."
    )

    # This radio button must stay OUTSIDE the form so the page refreshes immediately
    # when the user switches between Flat monthly number and Detailed monthly budget.
    budget_mode = st.radio(
        "How do you want to enter household spending?",
        ["Flat monthly number", "Detailed monthly budget"],
        index=0 if st.session_state.budget_mode == "Flat monthly number" else 1,
        key="budget_mode_selector",
        help="Choose flat monthly spending for a quick estimate, or detailed monthly budget to enter category-by-category spending."
    )

    st.session_state.budget_mode = budget_mode

    with st.form("budget_form"):
        if budget_mode == "Flat monthly number":
            flat_monthly_spending = st.number_input(
                "Total household spending per month before healthcare",
                min_value=0,
                value=int(st.session_state.flat_monthly_spending),
                step=500,
                help=FIELD_HELP["flat_monthly_spending"]
            )
            detailed_values = {}
        else:
            st.info("Detailed monthly budget is selected. The spending categories below are opened so you can enter each item.")

            flat_monthly_spending = st.session_state.flat_monthly_spending
            detailed_values = {}

            groups = [
                ("Housing", budget_keys[0:4]),
                ("Utilities & communications", budget_keys[4:11]),
                ("Food & household", budget_keys[11:14]),
                ("Cars & transportation", budget_keys[14:18]),
                ("Lifestyle", budget_keys[18:21]),
                ("Other", budget_keys[21:]),
            ]

            for group_name, keys in groups:
                with st.expander(group_name, expanded=True):
                    cols = st.columns(min(4, len(keys)))
                    for i, (key, label) in enumerate(keys):
                        with cols[i % len(cols)]:
                            detailed_values[key] = st.number_input(
                                f"{label} per month",
                                min_value=0,
                                value=int(st.session_state.get(key, 0) or 0),
                                step=50,
                                help=f"Enter your estimated monthly amount for {label.lower()}."
                            )

        st.subheader("Planned Spending Change")
        enable_spending_change = st.checkbox(
            "Change my spending at a certain age",
            value=bool(st.session_state.enable_spending_change),
            help="Use this if spending will change later in retirement, such as spending more early and less later."
        )

        if enable_spending_change:
            c1, c2 = st.columns(2)
            spending_change_age = c1.number_input(
                "Age when spending changes",
                min_value=0,
                max_value=110,
                value=int(st.session_state.spending_change_age),
                step=1,
                help="Enter the age when your new monthly spending should begin."
            )
            spending_change_monthly = c2.number_input(
                "New monthly spending amount",
                min_value=0,
                value=int(st.session_state.spending_change_monthly),
                step=500,
                help="Enter the new monthly spending amount before healthcare."
            )
            if spending_change_age > 0 and spending_change_monthly > 0:
                st.info(f"Spending will change to {money(spending_change_monthly)} per month starting at age {spending_change_age}.")
        else:
            spending_change_age = st.session_state.spending_change_age
            spending_change_monthly = st.session_state.spending_change_monthly

        survivor_spending = st.number_input(
            "Annual household spending after first spouse death, optional",
            min_value=0,
            value=int(st.session_state.survivor_spending),
            step=5000,
            help=FIELD_HELP["survivor_spending"]
        )

        save_budget = st.form_submit_button("Save budget")

    if save_budget:
        st.session_state.budget_mode = budget_mode
        st.session_state.flat_monthly_spending = flat_monthly_spending
        st.session_state.survivor_spending = survivor_spending
        st.session_state.enable_spending_change = enable_spending_change
        st.session_state.spending_change_age = spending_change_age
        st.session_state.spending_change_monthly = spending_change_monthly

        for k, v in detailed_values.items():
            st.session_state[k] = v

        st.success("Budget saved.")

    monthly = (
        st.session_state.flat_monthly_spending
        if st.session_state.budget_mode == "Flat monthly number"
        else detailed_monthly_budget_total()
    )

    c1, c2 = st.columns(2)
    c1.metric("Monthly Spending Before Healthcare", money(monthly))
    c2.metric("Annual Spending Before Healthcare", money(monthly * 12))

    if st.session_state.enable_spending_change and int(st.session_state.spending_change_age or 0) > 0:
        c3, c4 = st.columns(2)
        c3.metric("Spending Changes At Age", int(st.session_state.spending_change_age))
        c4.metric("New Monthly Spending", money(st.session_state.spending_change_monthly))


with tabs[3]:
    st.header("Other Income Builder")
    page_help(
        "Income Builder",
        "This page captures income besides portfolio withdrawals, such as pensions, rental income, part-time work, consulting, annuities, or business income. More reliable income usually reduces portfolio withdrawal pressure."
    )
    st.write("Add pension, rental income, annuity, side gig, consulting, business income, dividends, royalties, or other retirement income.")

    income_mode = st.radio(
        "How do you want to enter other income?",
        ["Simple income", "Advanced income builder"],
        index=0 if st.session_state.income_mode == "Simple income" else 1,
    )
    st.session_state.income_mode = income_mode

    if income_mode == "Simple income":
        with st.form("simple_income_form"):
            c1, c2, c3 = st.columns(3)
            simple_income = c1.number_input("Other annual income before taxes", min_value=0, value=st.session_state.simple_income, step=1000, help=FIELD_HELP["simple_income"])
            simple_income_start = c2.number_input("Start age", min_value=0, max_value=110, value=st.session_state.simple_income_start, help=FIELD_HELP["simple_income_start"])
            simple_income_end = c3.number_input("End age, use 0 if lifelong", min_value=0, max_value=120, value=st.session_state.simple_income_end, help=FIELD_HELP["simple_income_end"])
            c1, c2 = st.columns(2)
            simple_income_inflation = c1.checkbox("Inflation adjusted?", value=st.session_state.simple_income_inflation, help=FIELD_HELP["simple_income_inflation"])
            simple_income_reliability = c2.selectbox("Reliability", ["Guaranteed", "Variable"], index=0 if st.session_state.simple_income_reliability == "Guaranteed" else 1, help=FIELD_HELP["simple_income_reliability"])
            save_income = st.form_submit_button("Save simple income")
        if save_income:
            st.session_state.simple_income = simple_income
            st.session_state.simple_income_start = simple_income_start
            st.session_state.simple_income_end = simple_income_end
            st.session_state.simple_income_inflation = simple_income_inflation
            st.session_state.simple_income_reliability = simple_income_reliability
            st.success("Simple income saved.")
    else:
        edited = st.data_editor(
            st.session_state.income_sources_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Income name"),
                "Annual Amount": st.column_config.NumberColumn("Annual amount", min_value=0, step=1000),
                "Start Age": st.column_config.NumberColumn("Start age", min_value=0, max_value=110, step=1),
                "End Age": st.column_config.NumberColumn("End age", min_value=0, max_value=120, step=1, help="Use 0 if lifelong"),
                "Inflation Adjusted": st.column_config.CheckboxColumn("Inflation adjusted?"),
                "Taxable": st.column_config.CheckboxColumn("Taxable?"),
                "Owner": st.column_config.SelectboxColumn("Owner", options=["User", "Spouse", "Joint"]),
                "Reliability": st.column_config.SelectboxColumn("Reliability", options=["Guaranteed", "Variable"]),
                "Continues After First Death": st.column_config.CheckboxColumn("Continues after first death?"),
            },
            key="income_editor",
        )
        if st.button("Save advanced income sources"):
            st.session_state.income_sources_df = edited
            st.success("Advanced income sources saved.")

with tabs[4]:
    st.header("Spouse / Partner Questions")
    page_help(
        "Spouse Questions",
        "This page adds spouse or partner timing, healthcare, contributions, and Social Security. This matters because retirement timing, survivor benefits, and spending needs often change when two people are included."
    )

    has_spouse = st.checkbox(
        "Include spouse or partner in this plan?",
        value=st.session_state.has_spouse,
        help="Turn this on only if you want the plan to include a spouse or partner. Leave it off for an individual retirement plan."
    )

    # Store this immediately so the page redraws and spouse fields appear/disappear right away.
    st.session_state.has_spouse = has_spouse

    if has_spouse:
        st.info("Spouse / partner fields are included in this scenario.")

        with st.form("spouse_form"):
            c1, c2, c3 = st.columns(3)
            spouse_age = c1.number_input(
                "Spouse current age",
                min_value=0,
                max_value=110,
                value=st.session_state.spouse_age,
                help=FIELD_HELP["spouse_age"]
            )
            spouse_retire_age = c2.number_input(
                "Spouse retirement age",
                min_value=0,
                max_value=110,
                value=st.session_state.spouse_retire_age,
                help=FIELD_HELP["spouse_retire_age"]
            )
            spouse_plan_age = c3.number_input(
                "Spouse plan-through age",
                min_value=0,
                max_value=120,
                value=st.session_state.spouse_plan_age,
                help=FIELD_HELP["spouse_plan_age"]
            )

            c1, c2, c3, c4 = st.columns(4)
            spouse_annual_contribution = c1.number_input(
                "Spouse annual contributions",
                min_value=0,
                value=st.session_state.spouse_annual_contribution,
                step=5000,
                help=FIELD_HELP["spouse_annual_contribution"]
            )
            spouse_healthcare = c2.number_input(
                "Spouse annual healthcare",
                min_value=0,
                value=st.session_state.spouse_healthcare,
                step=1000,
                help=FIELD_HELP["spouse_healthcare"]
            )
            spouse_ss_age = c3.number_input(
                "Spouse Social Security age",
                62,
                70,
                st.session_state.spouse_ss_age,
                help=FIELD_HELP["spouse_ss_age"]
            )
            spouse_ss = c4.number_input(
                "Spouse annual Social Security",
                min_value=0,
                value=st.session_state.spouse_ss,
                step=1000,
                help=FIELD_HELP["spouse_ss"]
            )

            survivor_ss_strategy = st.selectbox(
                "Survivor Social Security strategy",
                ["Higher benefit continues", "User benefit only"],
                index=0 if st.session_state.survivor_ss_strategy == "Higher benefit continues" else 1,
                help="Usually, the surviving spouse keeps the higher Social Security benefit and loses the smaller one."
            )

            save_spouse = st.form_submit_button("Save spouse answers")

        if save_spouse:
            for k, v in {
                "has_spouse": has_spouse,
                "spouse_age": spouse_age,
                "spouse_retire_age": spouse_retire_age,
                "spouse_plan_age": spouse_plan_age,
                "spouse_annual_contribution": spouse_annual_contribution,
                "spouse_healthcare": spouse_healthcare,
                "spouse_ss_age": spouse_ss_age,
                "spouse_ss": spouse_ss,
                "survivor_ss_strategy": survivor_ss_strategy,
            }.items():
                st.session_state[k] = v

            st.success("Spouse / partner answers saved.")

    else:
        st.info("No spouse or partner is included in this scenario. The projection will run as an individual plan.")

        # Clear spouse values for individual plans so they do not accidentally affect projections.
        st.session_state.has_spouse = False
        st.session_state.spouse_age = 0
        st.session_state.spouse_retire_age = 0
        st.session_state.spouse_plan_age = 90
        st.session_state.spouse_annual_contribution = 0
        st.session_state.spouse_healthcare = 0
        st.session_state.spouse_ss_age = 62
        st.session_state.spouse_ss = 0
        st.session_state.survivor_ss_strategy = "Higher benefit continues"


with tabs[5]:
    st.header("Review Answers")
    page_help(
        "Review Answers",
        "This page summarizes your saved inputs before running the plan. Use it to catch missing or incorrect assumptions before trusting the results."
    )
    missing = required_missing()
    if missing:
        st.warning("Still missing: " + ", ".join(missing))
    else:
        st.success("Required answers are complete.")

    review = pd.DataFrame([
        ["Current age", st.session_state.current_age],
        ["Retirement age", st.session_state.retire_age],
        ["Plan-through age", st.session_state.end_age],
        ["Traditional", money(st.session_state.traditional)],
        ["Roth", money(st.session_state.roth)],
        ["Taxable", money(st.session_state.taxable)],
        ["Bucket 1 / Cash", money(st.session_state.cash)],
        ["Annual contributions", money(st.session_state.annual_contribution)],
        ["Budget mode", st.session_state.budget_mode],
        ["Annual spending before healthcare", money(annual_household_spending())],
        ["Spending change enabled", "Yes" if st.session_state.enable_spending_change else "No"],
        ["Spending change age", st.session_state.spending_change_age if st.session_state.enable_spending_change else "N/A"],
        ["New monthly spending", money(st.session_state.spending_change_monthly) if st.session_state.enable_spending_change else "N/A"],
        ["Income mode", st.session_state.income_mode],
        ["Simple other income", money(st.session_state.simple_income) if st.session_state.income_mode == "Simple income" else "Advanced table"],
        ["Plan type", "Couple / household plan" if st.session_state.has_spouse else "Individual plan"],
        ["Spouse age", st.session_state.spouse_age if st.session_state.has_spouse else "N/A"],
        ["Spouse retirement age", st.session_state.spouse_retire_age if st.session_state.has_spouse else "N/A"],
        ["Your SS", money(st.session_state.user_ss)],
        ["Spouse SS", money(st.session_state.spouse_ss) if st.session_state.has_spouse else "N/A"],
        ["Growth return", pct(st.session_state.growth_return)],
        ["Inflation", pct(st.session_state.inflation)],
        ["Home value", money(st.session_state.home_value)],
        ["Mortgage balance", money(st.session_state.mortgage_balance)],
        ["Estimated home equity", money(home_equity())],
        ["Monthly mortgage payment", money(st.session_state.monthly_mortgage)],
        ["Annual property taxes", money(st.session_state.annual_property_taxes_home)],
        ["Mortgage payoff age", st.session_state.mortgage_payoff_age if st.session_state.mortgage_payoff_age else "Unknown"],
        ["Housing plan", st.session_state.retirement_housing_plan],
    ], columns=["Input", "Answer"])
    st.dataframe(review, use_container_width=True)

can_run = len(required_missing()) == 0
df = run_projection() if can_run else pd.DataFrame()

with tabs[6]:
    st.header("Dashboard")
    page_help(
        "Dashboard",
        "This page shows the main retirement outcome. RTV means Retirement Timing Viability. It summarizes whether your plan appears funded, how much money may remain, income coverage, withdrawals, and risk areas."
    )
    if not can_run:
        st.info("Complete required inputs first.")
    else:
        ending = df["End Total"].iloc[-1]
        depleted = df["Unmet Need"].sum() > 0 or ending <= 0 or df["Age"].iloc[-1] < st.session_state.end_age
        rtv_score, rtv_label, rtv_reasons = calculate_rtv_score(df)


        summary_dashboard = {
            "traditional": float(st.session_state.traditional),
            "roth": float(st.session_state.roth),
            "taxable": float(st.session_state.taxable),
            "cash": float(st.session_state.cash),
            "total_assets": float(st.session_state.traditional) + float(st.session_state.roth) + float(st.session_state.taxable) + float(st.session_state.cash),
            "monthly_spending": annual_household_spending() / 12,
            "annual_spending": annual_household_spending(),
            "annual_income": float(df["Total Non-Portfolio Income"].mean()),
            "income_coverage": float(df["Income Coverage Ratio"].mean()),
            "rough_wr": float(df["Withdrawal Rate"].max()),
            "score": rtv_score,
            "retire_age": st.session_state.retire_age,
            "end_age": st.session_state.end_age,
            "growth_return": st.session_state.growth_return,
            "safe_return": st.session_state.safe_return,
            "inflation": st.session_state.inflation,
        }

        risk_scores = calculate_risk_scores(summary_dashboard)

        st.markdown("## Retirement Readiness Dashboard")

        hero1, hero2 = st.columns([1.1, 2])

        with hero1:
            st.markdown(f"""
            <div style="
                border-radius:24px;
                padding:28px;
                background:linear-gradient(135deg,#0f172a,#1e3a8a);
                color:white;
                text-align:center;
                box-shadow:0 6px 20px rgba(0,0,0,0.18);
            ">
                <div style="font-size:18px;font-weight:700;opacity:0.9;">
                    Retirement Timing Viability
                </div>
                <div style="font-size:70px;font-weight:900;line-height:1;">
                    {rtv_score}
                </div>
                <div style="
                    font-size:20px;
                    font-weight:700;
                    margin-top:8px;
                    color:#bfdbfe;
                ">
                    {rtv_label}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with hero2:
            rc1, rc2, rc3, rc4, rc5 = st.columns(5)

            rc1.metric("Sequence Risk", f"{risk_scores['Sequence Risk']}/100")
            rc2.metric("Tax Risk", f"{risk_scores['Tax Risk']}/100")
            rc3.metric("Healthcare Risk", f"{risk_scores['Healthcare Risk']}/100")
            rc4.metric("Longevity Risk", f"{risk_scores['Longevity Risk']}/100")
            rc5.metric("Income Stability", f"{100-risk_scores['Income Stability Risk']}/100")

            st.progress(rtv_score / 100)

            if rtv_score >= 90:
                st.success("Your retirement timing currently looks extremely strong under these assumptions.")
            elif rtv_score >= 75:
                st.success("Your retirement timing appears viable with moderate flexibility.")
            elif rtv_score >= 60:
                st.warning("Your plan may work, but optimization opportunities remain.")
            else:
                st.error("Your current retirement timing assumptions appear aggressive.")

        st.subheader("RTV - Retirement Timing Viability")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("RTV Score", f"{rtv_score}/100", rtv_label)
        c2.metric("Outcome", "Funded" if not depleted else "Needs Work")
        c3.metric("Ending Portfolio", money(ending))
        c4.metric("Max Withdrawal Rate", pct(df["Withdrawal Rate"].max()))
        c5.metric("Income Coverage", pct(df["Income Coverage Ratio"].mean()))

        st.progress(rtv_score / 100)

        if rtv_score >= 90:
            st.success("RTV: Very strong retirement timing viability.")
        elif rtv_score >= 75:
            st.success("RTV: Your target retirement age appears likely viable.")
        elif rtv_score >= 60:
            st.warning("RTV: Your plan may work, but it needs optimization.")
        else:
            st.error("RTV: Your retirement timing appears high risk under current assumptions.")

        with st.expander("Why did I get this RTV score?"):
            if rtv_reasons:
                for reason in rtv_reasons:
                    st.write(f"- {reason}")
            else:
                st.write("No major risk flags found.")

        st.caption("RTV is an educational score based on portfolio longevity, max withdrawal rate, income coverage, and unmet spending needs.")

        st.subheader("Home & Housing Strategy")
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Home Value", money(st.session_state.home_value))
        h2.metric("Mortgage Balance", money(st.session_state.mortgage_balance))
        h3.metric("Home Equity", money(home_equity()), housing_flexibility_label())
        h4.metric("Housing Plan", st.session_state.retirement_housing_plan)

        if float(st.session_state.monthly_mortgage or 0) > 0:
            if int(st.session_state.mortgage_payoff_age or 0) > int(st.session_state.retire_age or 0):
                st.warning("Your mortgage appears to continue into retirement. This can increase early retirement cash-flow pressure.")
            else:
                st.success("Your mortgage appears to be paid off by retirement age, based on your payoff-age input.")

        if st.session_state.retirement_housing_plan in ["Downsize", "Relocate", "Snowbird"]:
            st.info("Your housing plan may create flexibility. Downsizing, relocating, or snowbirding can reduce expenses, unlock equity, or change state tax exposure.")

        st.subheader("Portfolio Balance")
        st.caption("Shows how each account type contributes to your total projected portfolio over time.")
        st.pyplot(plot_portfolio_area_chart(df), use_container_width=True)

        st.subheader("Spending, Income, and Portfolio Withdrawal")
        st.caption("Compares annual spending, outside income, and how much must come from the portfolio.")
        st.pyplot(plot_spending_income_bar_chart(df), use_container_width=True)

        st.subheader("Income Gap")
        st.caption("Shows how much spending is not covered by guaranteed/outside income and must be filled by portfolio withdrawals.")
        st.pyplot(plot_income_gap_chart(df), use_container_width=True)

        st.subheader("Withdrawal Rate Pressure")
        st.caption("Shows the annual withdrawal rate against 4% and 6% reference lines.")
        st.pyplot(plot_withdrawal_rate_chart(df), use_container_width=True)

with tabs[7]:
    st.header("Recommendations")
    page_help(
        "Recommendations",
        "This page tests ways to improve your RTV score, such as retiring later, spending less, contributing more, or changing Social Security timing. It also tests whether you may be able to spend more and still keep a strong score."
    )
    st.caption("Practical ways to improve your RTV score and understand whether you can safely spend more.")

    if not can_run:
        st.info("Complete required inputs first.")
    else:
        depleted = df["Unmet Need"].sum() > 0 or df["End Total"].iloc[-1] <= 0 or df["Age"].iloc[-1] < st.session_state.end_age
        max_wr = df["Withdrawal Rate"].max()
        avg_wr = df["Withdrawal Rate"].mean()
        rtv_score, rtv_label, rtv_reasons = calculate_rtv_score(df)
        ending_portfolio = df["End Total"].iloc[-1]
        avg_income_coverage = df["Income Coverage Ratio"].mean()

        st.subheader("Your Retirement Timing Viability")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("RTV Score", f"{rtv_score}/100", rtv_label)
        c2.metric("Ending Portfolio", money(ending_portfolio))
        c3.metric("Max Withdrawal Rate", pct(max_wr))
        c4.metric("Income Coverage", pct(avg_income_coverage))

        st.progress(rtv_score / 100)

        if rtv_score >= 90:
            st.success("Your plan looks very strong under these assumptions.")
        elif rtv_score >= 80:
            st.success("Your plan looks strong, but there may still be optimization opportunities.")
        elif rtv_score >= 70:
            st.warning("Your plan appears likely viable, but improvements could increase confidence.")
        elif rtv_score >= 60:
            st.warning("Your plan may work, but it needs optimization.")
        else:
            st.error("Your current plan appears high risk under these assumptions.")

        if rtv_reasons:
            with st.expander("Why this score?"):
                for reason in rtv_reasons:
                    st.write(f"- {reason}")

        st.divider()

        st.subheader("How to Improve Your RTV Score")

        actions = build_rtv_improvement_recommendations(df, rtv_score)
        positive_actions = [a for a in actions if a["RTV Impact"] > 0]

        if positive_actions:
            best = positive_actions[0]
            st.success(
                f"Highest-impact action: **{best['Action']}** could move RTV from "
                f"**{rtv_score} to {best['New RTV']}**."
            )

            action_df = pd.DataFrame(positive_actions[:8])
            action_df["RTV Impact"] = action_df["RTV Impact"].map(lambda x: f"+{x}" if x > 0 else str(x))
            action_df["Ending Portfolio"] = action_df["Ending Portfolio"].map(money)
            action_df["Max Withdrawal Rate"] = action_df["Max Withdrawal Rate"].map(pct)
            action_df["Income Coverage"] = action_df["Income Coverage"].map(pct)
            action_df["Unmet Need"] = action_df["Unmet Need"].map(money)

            st.dataframe(action_df, use_container_width=True, hide_index=True)
        else:
            st.info("Your current score is already strong or the tested changes did not materially improve RTV.")

        st.markdown("### Plain-English Recommendations")

        if max_wr > 0.07:
            st.write("- **Reduce withdrawal pressure:** Try lowering spending, delaying retirement, or adding income before retirement.")
        elif max_wr > 0.05:
            st.write("- **Watch early withdrawals:** Your plan may benefit from a larger Bucket 1 or slightly lower early-retirement spending.")
        else:
            st.write("- **Withdrawal pressure looks reasonable:** Your current spending level appears manageable in the projection.")

        if avg_income_coverage < 0.30:
            st.write("- **Increase reliable income:** Consider Social Security timing, part-time income, pension options, or guaranteed income strategies.")
        elif avg_income_coverage < 0.60:
            st.write("- **Income coverage is moderate:** Your portfolio still matters, but outside income is helping.")
        else:
            st.write("- **Income coverage is strong:** Outside income is carrying a meaningful part of the plan.")

        if ending_portfolio > float(st.session_state.traditional + st.session_state.roth + st.session_state.taxable + st.session_state.cash):
            st.write("- **You may have room for more spending:** Your ending balance is higher than your starting balance.")
        elif ending_portfolio > 500000:
            st.write("- **You have a healthy ending cushion:** The plan survives with meaningful assets remaining.")
        else:
            st.write("- **Protect the cushion:** Your ending balance is not huge, so avoid aggressive spending increases.")

        if st.session_state.end_age > 90:
            st.write("- **Long planning horizon:** Planning past age 90 is conservative. Reducing the planning age can raise RTV, but it also lowers longevity protection.")
        elif st.session_state.end_age < 90:
            st.write("- **Shorter planning horizon:** This can improve the score, but make sure it matches your longevity assumptions.")

        st.divider()

        st.subheader("Can You Spend More?")

        spend_more_rows = build_spend_more_tests(rtv_score)

        if spend_more_rows:
            spend_df = pd.DataFrame(spend_more_rows)
            safe_spend = spend_df[spend_df["New RTV"] >= 80]

            if not safe_spend.empty:
                best_spend = safe_spend.iloc[-1]
                st.success(
                    f"You may be able to spend more. Tested increase: **{best_spend['Scenario']}** "
                    f"still leaves RTV at **{int(best_spend['New RTV'])}**."
                )
            else:
                st.warning("The tested spending increases lower RTV below the strong range. Increase spending carefully.")

            spend_df["New Monthly Spending"] = spend_df["New Monthly Spending"].map(money)
            spend_df["RTV Impact"] = spend_df["RTV Impact"].map(lambda x: f"{x:+}")
            spend_df["Ending Portfolio"] = spend_df["Ending Portfolio"].map(money)
            spend_df["Max Withdrawal Rate"] = spend_df["Max Withdrawal Rate"].map(pct)

            st.dataframe(spend_df, use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("Spending Target Finder")
        st.write(
            "This tool estimates what monthly spending level may help the plan reach a target RTV score. "
            "It can also show whether the plan may support more spending."
        )

        target_rtv_score = st.slider(
            "Target RTV score",
            min_value=60,
            max_value=95,
            value=80,
            step=5,
            help="Higher targets are more conservative. 80 is a reasonable starting point for a likely viable plan."
        )

        if st.button("Find Suggested Monthly Spending"):
            try:
                spending_result = find_monthly_spending_for_target_score(target_rtv_score)

                if spending_result is None:
                    st.warning("Add household spending and complete the required inputs before using the Spending Target Finder.")
                elif spending_result["suggested_monthly"] is None:
                    st.error("The plan could not reach the target RTV score by reducing spending alone. Try a later retirement age, more contributions, more income, or lower healthcare/housing costs.")
                else:
                    current_monthly = spending_result["current_monthly"]
                    suggested_monthly = spending_result["suggested_monthly"]
                    monthly_difference = spending_result["monthly_difference"]

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Current Monthly Spending", money(current_monthly))
                    c2.metric("Suggested Monthly Spending", money(suggested_monthly))
                    c3.metric("Monthly Difference", money(monthly_difference))
                    c4.metric("Estimated RTV Score", f"{spending_result['suggested_score']}/100", spending_result["suggested_label"])

                    if spending_result["mode"] == "lower":
                        st.warning(
                            f"To target an RTV score of {target_rtv_score}+, consider lowering spending by about "
                            f"{money(abs(monthly_difference))} per month."
                        )
                    else:
                        if suggested_monthly > current_monthly * 1.02:
                            st.success(
                                f"Your plan may support about {money(monthly_difference)} more spending per month "
                                f"while still targeting an RTV score of {target_rtv_score}+."
                            )
                        else:
                            st.info(
                                f"Your current spending is close to the estimated sustainable level for an RTV score of {target_rtv_score}+."
                            )

                    st.caption(
                        "This is an educational estimate. It uses the app's RTV model and current assumptions, not financial advice."
                    )

            except Exception as e:
                st.error(f"Spending Target Finder could not run: {e}")

        st.divider()

        st.subheader("Spending Change Recommendations")
        if st.session_state.enable_spending_change and int(st.session_state.spending_change_age or 0) > 0:
            old_monthly = annual_household_spending() / 12
            new_monthly = float(st.session_state.spending_change_monthly or 0)
            change_age = int(st.session_state.spending_change_age or 0)

            if new_monthly < old_monthly:
                st.success(f"Your plan models lower spending starting at age {change_age}. This can improve long-term sustainability and reduce portfolio withdrawals.")
            elif new_monthly > old_monthly:
                st.warning(f"Your plan models higher spending starting at age {change_age}. Make sure the stress tests and Monte Carlo results still remain healthy.")
            else:
                st.info("Your later spending amount is the same as your current spending estimate.")
        else:
            st.info("Consider adding a later-life spending change if you expect spending to drop after travel, mortgage payoff, or other early-retirement expenses decline.")

        st.divider()

        st.subheader("Home & Housing Recommendations")
        equity = home_equity()
        payoff_age = int(st.session_state.mortgage_payoff_age or 0)
        retire_age_val = int(st.session_state.retire_age or 0)
        monthly_mort = float(st.session_state.monthly_mortgage or 0)
        annual_prop_tax = float(st.session_state.annual_property_taxes_home or 0)

        if equity >= 500000:
            st.success("High housing flexibility: substantial home equity may provide options for downsizing, relocation, cash reserves, or legacy planning.")
        elif equity >= 250000:
            st.info("Moderate housing flexibility: home equity could become an important retirement planning lever.")
        elif float(st.session_state.home_value or 0) > 0:
            st.warning("Lower home equity: your home may provide less flexibility unless the mortgage is reduced or the home appreciates.")

        if monthly_mort > 0 and payoff_age > retire_age_val:
            st.warning("Mortgage continues into retirement: test whether paying it down faster, refinancing, or downsizing improves your RTV score.")
        elif monthly_mort > 0 and payoff_age > 0:
            st.success("Mortgage payoff appears to happen before or around retirement, which may reduce retirement cash-flow pressure.")

        if annual_prop_tax >= 10000:
            st.warning("High property taxes: compare your current state/location against lower-tax retirement locations in the Best Places to Retire section.")
        elif annual_prop_tax > 0:
            st.info("Property taxes are included as a housing planning factor. Lower taxes may improve long-term retirement spending flexibility.")

        if st.session_state.retirement_housing_plan == "Downsize":
            st.success("Downsizing strategy: consider modeling a lower monthly budget and adding unlocked home equity to cash/taxable assets.")
        elif st.session_state.retirement_housing_plan == "Relocate":
            st.info("Relocation strategy: compare taxes, cost of living, healthcare access, and property taxes before choosing a retirement location.")
        elif st.session_state.retirement_housing_plan == "Snowbird":
            st.info("Snowbird strategy: model duplicate housing costs, travel, insurance, taxes, and whether renting first is safer than buying.")

        st.divider()

        st.subheader("When Should You Retire?")
        st.caption("Portfolio at Retirement shows the balance when that retirement age begins. End of Plan Portfolio shows the amount left at the final plan age.")

        possible = []
        original = st.session_state.retire_age

        for test_age in range(max(int(st.session_state.current_age), 18), min(int(st.session_state.end_age), 75) + 1):
            st.session_state.retire_age = test_age
            tdf = run_projection()

            if not tdf.empty:
                test_score, test_label, _ = calculate_rtv_score(tdf)
                t_depleted = tdf["Unmet Need"].sum() > 0 or tdf["End Total"].iloc[-1] <= 0 or tdf["Age"].iloc[-1] < st.session_state.end_age

                # Portfolio at Retirement = balance when retirement begins in this test scenario.
                # End of Plan Portfolio = balance left at the final plan age.
                retirement_row = tdf[tdf["Age"] == test_age]
                if not retirement_row.empty:
                    portfolio_at_retirement = retirement_row["Start Total"].iloc[0]
                else:
                    portfolio_at_retirement = tdf["Start Total"].iloc[0]

                possible.append({
                    "Retirement Age": test_age,
                    "RTV Score": test_score,
                    "RTV Label": test_label,
                    "Portfolio at Retirement": portfolio_at_retirement,
                    "End of Plan Portfolio": tdf["End Total"].iloc[-1],
                    "Max Withdrawal Rate": tdf["Withdrawal Rate"].max(),
                    "Avg Income Coverage": tdf["Income Coverage Ratio"].mean(),
                    "Result": "Good" if (not t_depleted and test_score >= 80) else ("Possible" if not t_depleted else "Too Risky"),
                })

        st.session_state.retire_age = original

        rdf = pd.DataFrame(possible)

        if not rdf.empty:
            good = rdf[rdf["Result"] == "Good"]
            ok = rdf[rdf["Result"].isin(["Good", "Possible"])]

            if not good.empty:
                st.success(f"Recommended retirement age: **{int(good['Retirement Age'].iloc[0])}**")
            elif not ok.empty:
                st.warning(f"Earliest possible retirement age: **{int(ok['Retirement Age'].iloc[0])}**, but it may be aggressive.")
            else:
                st.error("No tested retirement age looked funded.")

            show = rdf.copy()
            show["Portfolio at Retirement"] = show["Portfolio at Retirement"].map(money)
            show["End of Plan Portfolio"] = show["End of Plan Portfolio"].map(money)
            show["Max Withdrawal Rate"] = show["Max Withdrawal Rate"].map(pct)
            show["Avg Income Coverage"] = show["Avg Income Coverage"].map(pct)
            st.dataframe(show, use_container_width=True, hide_index=True)

with tabs[8]:
    st.header("Projection Table")
    page_help(
        "Projection Table",
        "This table shows the year-by-year math behind the plan. It includes balances, spending, income, withdrawals, Roth conversions, unmet needs, and withdrawal rates by age."
    )
    if not can_run:
        st.info("Complete required inputs first.")
    else:
        show = df.copy()
        money_cols = [c for c in show.columns if c not in ["Age", "Spouse Age", "Spouse Alive", "Household Retired", "Withdrawal Rate", "Income Coverage Ratio", "Guaranteed Income Coverage Ratio"]]
        for c in money_cols:
            show[c] = show[c].map(money)
        show["Withdrawal Rate"] = show["Withdrawal Rate"].map(pct)
        show["Income Coverage Ratio"] = show["Income Coverage Ratio"].map(pct)
        show["Guaranteed Income Coverage Ratio"] = show["Guaranteed Income Coverage Ratio"].map(pct)
        st.dataframe(show, use_container_width=True)
        st.download_button("Download Projection CSV", df.to_csv(index=False).encode("utf-8"), "retirement_projection.csv", "text/csv")

with tabs[9]:
    st.markdown("""
    <style>
    /* Saved Scenarios page polish */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border-radius: 12px;
        padding: 8px 10px;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.45rem;
        font-weight: 800;
        color: #111827;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem;
        color: #374151;
        font-weight: 650;
    }

    .saved-page-title {
        font-size: 2.05rem;
        line-height: 1.1;
        font-weight: 850;
        color: #111827;
        margin-bottom: 0.25rem;
    }

    .saved-page-caption {
        font-size: 1rem;
        color: #4b5563;
        margin-bottom: 1.5rem;
    }

    .scenario-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding-bottom: 8px;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 14px;
    }

    .scenario-title-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
    }

    .scenario-title {
        font-size: 1.35rem;
        font-weight: 850;
        color: #111827;
    }

    .scenario-date {
        color: #4b5563;
        font-size: 0.92rem;
        white-space: nowrap;
    }

    .badge-current {
        display: inline-block;
        padding: 4px 11px;
        border-radius: 999px;
        background: #dbeafe;
        color: #1d4ed8;
        font-size: 0.78rem;
        font-weight: 800;
    }

    .badge-strong {
        display: inline-block;
        padding: 4px 11px;
        border-radius: 999px;
        background: #dcfce7;
        color: #15803d;
        font-size: 0.78rem;
        font-weight: 800;
    }

    .badge-work {
        display: inline-block;
        padding: 4px 11px;
        border-radius: 999px;
        background: #ffedd5;
        color: #ea580c;
        font-size: 0.78rem;
        font-weight: 800;
    }

    .badge-risk {
        display: inline-block;
        padding: 4px 11px;
        border-radius: 999px;
        background: #fee2e2;
        color: #dc2626;
        font-size: 0.78rem;
        font-weight: 800;
    }

    .section-title {
        font-weight: 850;
        font-size: 1rem;
        margin-bottom: 0.65rem;
        color: #111827;
    }

    .kv-row {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid #f1f5f9;
        padding: 6px 0;
        font-size: 0.93rem;
    }

    .kv-left {
        color: #475569;
    }

    .kv-right {
        color: #111827;
        font-weight: 750;
    }

    .score-big {
        font-size: 2.15rem;
        font-weight: 900;
        line-height: 1.0;
        color: #16a34a;
    }

    .score-big-warning {
        color: #f97316;
    }

    .score-big-risk {
        color: #dc2626;
    }

    .tiny-caption {
        color: #64748b;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='saved-page-title'>Saved Scenarios</div>", unsafe_allow_html=True)
    st.markdown("<div class='saved-page-caption'>Save, load, compare, and generate AI recommendations for your retirement plans.</div>", unsafe_allow_html=True)

    if "compare_scenarios" not in st.session_state:
        st.session_state.compare_scenarios = {}

    if "saved_ai_recommendations" not in st.session_state:
        st.session_state.saved_ai_recommendations = {}

    def scenario_summary_from_data(data):
        traditional = float(data.get("traditional", 0) or 0)
        roth = float(data.get("roth", 0) or 0)
        taxable = float(data.get("taxable", 0) or 0)
        cash = float(data.get("cash", 0) or 0)
        total_assets = traditional + roth + taxable + cash

        monthly_spending = float(data.get("flat_monthly_spending", 0) or 0)
        annual_spending = monthly_spending * 12

        user_ss = float(data.get("user_ss", 0) or 0)
        spouse_ss = float(data.get("spouse_ss", 0) or 0) if data.get("has_spouse", False) else 0
        simple_income = float(data.get("simple_income", 0) or 0)
        annual_income = user_ss + spouse_ss + simple_income

        income_coverage = annual_income / annual_spending if annual_spending > 0 else 0

        retire_age = int(data.get("retire_age", 0) or 0)
        current_age = int(data.get("current_age", 0) or 0)
        end_age = int(data.get("end_age", 90) or 90)
        years_to_retire = max(retire_age - current_age, 0)

        rough_wr = max(annual_spending - annual_income, 0) / total_assets if total_assets > 0 else 0

        # Use the real projection engine for saved scenario math.
        projection_df, score, label, rtv_reasons = run_projection_for_saved_scenario(data)

        if not projection_df.empty:
            annual_income = float(projection_df["Total Non-Portfolio Income"].mean())
            income_coverage = float(projection_df["Income Coverage Ratio"].mean())
            rough_wr = float(projection_df["Withdrawal Rate"].max())
            ending_portfolio = float(projection_df["End Total"].iloc[-1])
            unmet_need = float(projection_df["Unmet Need"].sum())
        else:
            ending_portfolio = 0
            unmet_need = 0

        if score >= 90:
            badge = "badge-strong"
            score_class = "score-big"
        elif score >= 75:
            badge = "badge-strong"
            score_class = "score-big"
        elif score >= 60:
            badge = "badge-work"
            score_class = "score-big score-big-warning"
        else:
            badge = "badge-risk"
            score_class = "score-big score-big-risk"

        return {
            "traditional": traditional,
            "roth": roth,
            "taxable": taxable,
            "cash": cash,
            "total_assets": total_assets,
            "monthly_spending": monthly_spending,
            "annual_spending": annual_spending,
            "user_ss": user_ss,
            "spouse_ss": spouse_ss,
            "simple_income": simple_income,
            "annual_income": annual_income,
            "income_coverage": income_coverage,
            "rough_wr": rough_wr,
            "ending_portfolio": ending_portfolio,
            "unmet_need": unmet_need,
            "rtv_reasons": rtv_reasons,
            "score": score,
            "label": label,
            "badge": badge,
            "score_class": score_class,
            "current_age": current_age,
            "retire_age": retire_age,
            "end_age": end_age,
            "years_to_retire": years_to_retire,
            "growth_return": float(data.get("growth_return", 0) or 0),
            "safe_return": float(data.get("safe_return", 0) or 0),
            "inflation": float(data.get("inflation", 0) or 0),
            "bucket1_years": float(data.get("bucket1_years", 0) or 0),
            "annual_conversion": float(data.get("annual_conversion", 0) or 0),
        }

    def make_template_data(template_name):
        data = get_scenario_data()

        if template_name == "Conservative":
            data["growth_return"] = 0.055
            data["safe_return"] = 0.035
            data["inflation"] = 0.035
            data["bucket1_years"] = 4.0
            if float(data.get("flat_monthly_spending", 0) or 0) > 0:
                data["flat_monthly_spending"] = round(float(data["flat_monthly_spending"]) * 1.05)
            data["annual_conversion"] = 0

        elif template_name == "Base":
            data["growth_return"] = 0.07
            data["safe_return"] = 0.045
            data["inflation"] = 0.03
            data["bucket1_years"] = 3.0

        elif template_name == "Aggressive":
            data["growth_return"] = 0.085
            data["safe_return"] = 0.045
            data["inflation"] = 0.03
            data["bucket1_years"] = 2.0
            if int(data.get("retire_age", 0) or 0) > 0:
                data["retire_age"] = max(int(data["retire_age"]) - 2, int(data.get("current_age", 0) or 0))

        return data

    def generate_recommendations_for_summary(summary):
        recs = []

        if summary["score"] >= 85:
            recs.append("This scenario looks strong. Focus on protecting the plan from taxes, healthcare surprises, and sequence-of-return risk.")
        elif summary["score"] >= 70:
            recs.append("This scenario may be viable, but it should be stress-tested before relying on it.")
        else:
            recs.append("This scenario needs work before it should be considered a confident retirement plan.")

        if summary["rough_wr"] > 0.06:
            recs.append("Withdrawal pressure looks high. Consider delaying retirement, lowering spending, increasing guaranteed income, or building more assets.")
        elif summary["rough_wr"] > 0.04:
            recs.append("Withdrawal pressure is moderate. A stronger cash bucket or lower early-retirement spending could improve confidence.")

        if summary["income_coverage"] < 0.40:
            recs.append("Outside income covers a relatively small share of spending. Social Security timing, part-time income, pension income, or annuity analysis may help.")
        elif summary["income_coverage"] >= 0.70:
            recs.append("Income coverage is strong. This reduces pressure on the portfolio.")

        if summary["cash"] < summary["annual_spending"] * 1.5 and summary["annual_spending"] > 0:
            recs.append("Bucket 1/cash may be light. Consider holding 2–4 years of spending needs in safer assets before retirement.")

        if summary["traditional"] > summary["roth"] * 3 and summary["traditional"] > 250000:
            recs.append("Traditional retirement assets are much larger than Roth. Roth conversion planning may reduce future tax risk.")

        return recs

    def build_pdf_report_bytes(name, data, summary, recommendations):
        buffer = io.BytesIO()
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.08, 0.94, "Retirement Scenario Report", fontsize=22, weight="bold")
        fig.text(0.08, 0.90, name, fontsize=16, weight="bold")

        y = 0.84
        lines = [
            f"RTV Score: {summary['score']}/100 ({summary['label']})",
            f"Current Age: {summary['current_age']}",
            f"Retirement Age: {summary['retire_age']}",
            f"Plan Until Age: {summary['end_age']}",
            f"Total Assets: {money(summary['total_assets'])}",
            f"Traditional: {money(summary['traditional'])}",
            f"Roth: {money(summary['roth'])}",
            f"Taxable: {money(summary['taxable'])}",
            f"Cash / Bucket 1: {money(summary['cash'])}",
            f"Monthly Spending: {money(summary['monthly_spending'])}",
            f"Annual Spending: {money(summary['annual_spending'])}",
            f"Annual Income: {money(summary['annual_income'])}",
            f"Income Coverage: {pct(summary['income_coverage'])}",
            f"Estimated Max Withdrawal Rate: {pct(summary['rough_wr'])}",
            f"Growth Return: {pct(summary['growth_return'])}",
            f"Inflation: {pct(summary['inflation'])}",
            f"Safe Return: {pct(summary['safe_return'])}",
            f"Bucket 1 Years: {summary['bucket1_years']:.1f}",
            f"Annual Roth Conversion: {money(summary['annual_conversion'])}",
        ]

        fig.text(0.08, y, "Scenario Snapshot", fontsize=14, weight="bold")
        y -= 0.035

        for line in lines:
            fig.text(0.10, y, line, fontsize=10)
            y -= 0.028

        y -= 0.015
        fig.text(0.08, y, "Recommendations", fontsize=14, weight="bold")
        y -= 0.035

        for rec in recommendations:
            fig.text(0.10, y, f"- {rec}", fontsize=9)
            y -= 0.045

        fig.text(
            0.08,
            0.06,
            "Educational planning tool only. Not financial, tax, legal, investment, or insurance advice.",
            fontsize=8,
            color="gray"
        )

        fig.savefig(buffer, format="pdf", bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)
        return buffer.getvalue()

    def blank_scenario_data():
        data = {k: v for k, v in defaults.items()}
        for k, _ in budget_keys:
            data[k] = 0
        data["income_sources_df"] = []
        return data

    if not user:
        st.info("Log in to save and load retirement scenarios.")
    else:
        st.subheader("Save Current Scenario")

        save_col1, save_col2 = st.columns([5, 1.25])
        with save_col1:
            scenario_name = st.text_input("Scenario name", "My Retirement Plan", label_visibility="visible")
        with save_col2:
            st.write("")
            st.write("")
            save_clicked = st.button("💾 Save Scenario", use_container_width=True, type="primary")

        if save_clicked:
            try:
                scenario_data = get_scenario_data()
                save_scenario(user, scenario_name, scenario_data)
                st.success("Scenario saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Scenario save failed: {e}")

        st.divider()

        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.subheader("Your Saved Scenarios")
        with col_b:
            if st.button("⟳ Refresh", use_container_width=True):
                st.rerun()

        try:
            scenarios = load_scenarios(user)
        except Exception as e:
            st.error(f"Could not load scenarios: {e}")
            scenarios = []

        if not scenarios:
            st.info("No saved scenarios yet.")
        else:
            # Scenario Comparison panel
            if st.session_state.compare_scenarios:
                st.markdown("### Scenario Comparison")
                st.caption("Compare your saved retirement plans side by side.")

                compare_items = []
                for sid, item in st.session_state.compare_scenarios.items():
                    data = item["data"]
                    s = scenario_summary_from_data(data)
                    compare_items.append({
                        "id": sid,
                        "name": item["name"],
                        "summary": s,
                    })

                best = max(
                    compare_items,
                    key=lambda x: (
                        x["summary"]["score"],
                        x["summary"]["income_coverage"],
                        x["summary"]["total_assets"],
                    )
                )

                st.success(
                    f"Best current option: **{best['name']}** "
                    f"with an RTV score of **{best['summary']['score']}** "
                    f"({best['summary']['label']})."
                )

                card_cols = st.columns(min(len(compare_items), 3))
                for i, item in enumerate(compare_items):
                    s = item["summary"]
                    with card_cols[i % len(card_cols)]:
                        with st.container(border=True):
                            st.subheader(item["name"])
                            st.metric("RTV Score", f"{s['score']}/100", s["label"])
                            st.progress(s["score"] / 100)
                            st.write(f"Retire Age: **{s['retire_age']}**")
                            st.write(f"Total Assets: **{money(s['total_assets'])}**")
                            st.write(f"Monthly Spending: **{money(s['monthly_spending'])}**")
                            st.write(f"Annual Income: **{money(s['annual_income'])}**")
                            st.write(f"Income Coverage: **{pct(s['income_coverage'])}**")
                            st.write(f"Max Withdrawal Rate: **{pct(s['rough_wr'])}**")

                compare_rows = []
                for item in compare_items:
                    s = item["summary"]
                    compare_rows.append({
                        "Scenario": item["name"],
                        "RTV Score": s["score"],
                        "Status": s["label"],
                        "Retire Age": s["retire_age"],
                        "Plan Until": s["end_age"],
                        "Total Assets": money(s["total_assets"]),
                        "Monthly Spending": money(s["monthly_spending"]),
                        "Annual Income": money(s["annual_income"]),
                        "Income Coverage": pct(s["income_coverage"]),
                        "Max Withdrawal Rate": pct(s["rough_wr"]),
                    })

                st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)

                if len(compare_items) >= 2:
                    sorted_items = sorted(compare_items, key=lambda x: x["summary"]["score"], reverse=True)
                    top = sorted_items[0]
                    bottom = sorted_items[-1]
                    score_gap = top["summary"]["score"] - bottom["summary"]["score"]

                    st.markdown("#### What Changed?")
                    headline, insights = explain_scenario_changes(top["summary"], bottom["summary"])
                    st.success(headline)
                    for insight in insights:
                        st.write(f"• {insight}")

                    st.info(
                        f"**{top['name']}** currently scores **{score_gap} points higher** than "
                        f"**{bottom['name']}**."
                    )

                clear_col, note_col = st.columns([1, 4])
                with clear_col:
                    if st.button("Clear Compare", use_container_width=True):
                        st.session_state.compare_scenarios = {}
                        st.rerun()
                with note_col:
                    st.caption("Tip: compare 2 or 3 plans for the cleanest readout.")

                st.divider()

            for idx, scenario in enumerate(scenarios):
                data = scenario["scenario_data"]
                summary = scenario_summary_from_data(data)
                sid = str(scenario["id"])
                is_selected = sid in st.session_state.compare_scenarios
                selected_text = "Selected" if is_selected else ""
                recommendations = generate_recommendations_for_summary(summary)

                expander_label = f"{scenario['scenario_name']}  •  {summary['label']}"
                with st.expander(expander_label, expanded=(idx == 0)):
                    st.markdown(
                        f"""
                        <div class="scenario-card-header">
                            <div class="scenario-title-wrap">
                                <span class="scenario-title">{scenario['scenario_name']}</span>
                                <span class="{summary['badge']}">{summary['label']}</span>
                                {"<span class='badge-current'>Current</span>" if idx == 0 else ""}
                                {f"<span class='badge-work'>{selected_text}</span>" if selected_text else ""}
                            
                            
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.caption(f"Saved on: {scenario.get('created_at', '')}")

                    m1, m2, m3, m4, m5, m6 = st.columns([1, 1, 1.15, 1.15, 1.15, 0.95])
                    m1.metric("🗓️ Retire Age", summary["retire_age"])
                    m2.metric("👥 Plan Until", summary["end_age"])
                    m3.metric("💵 Total Assets", money(summary["total_assets"]))
                    m4.metric("🛒 Monthly Spending", money(summary["monthly_spending"]))
                    m5.metric("💼 Income Annual", money(summary["annual_income"]))

                    with m6:
                        st.markdown("RTV Score")
                        st.markdown(
                            f"<div class='{summary['score_class']}'>{summary['score']}</div>"
                            f"<div class='tiny-caption'>{summary['label']}</div>",
                            unsafe_allow_html=True
                        )

                    st.divider()

                    left, middle, right = st.columns([1.25, 1.05, 1.15])

                    with left:
                        st.markdown("<div class='section-title'>Asset Breakdown</div>", unsafe_allow_html=True)

                        asset_rows = pd.DataFrame({
                            "Account": ["Traditional", "Roth", "Taxable", "Cash / Bucket 1"],
                            "Amount": [summary["traditional"], summary["roth"], summary["taxable"], summary["cash"]],
                        })
                        asset_rows = asset_rows[asset_rows["Amount"] > 0]

                        if not asset_rows.empty:
                            fig_saved, ax_saved = plt.subplots(figsize=(3.25, 3.25))
                            wedges, _ = ax_saved.pie(
                                asset_rows["Amount"],
                                startangle=90,
                                wedgeprops=dict(width=0.42)
                            )
                            ax_saved.axis("equal")
                            ax_saved.legend(
                                wedges,
                                asset_rows["Account"],
                                title="Accounts",
                                loc="center left",
                                bbox_to_anchor=(1.0, 0.5),
                                fontsize=8
                            )
                            st.pyplot(fig_saved, use_container_width=True)

                            st.caption("Account values by color")
                            for _, row in asset_rows.iterrows():
                                pct_val = row["Amount"] / summary["total_assets"] if summary["total_assets"] > 0 else 0
                                st.markdown(
                                    f"""
                                    <div class="kv-row">
                                        <span class="kv-left">{row['Account']}</span>
                                        <span class="kv-right">{money(row['Amount'])} ({pct(pct_val)})</span>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                        else:
                            st.info("No asset balances saved yet.")

                    with middle:
                        st.markdown("<div class='section-title'>Key Assumptions</div>", unsafe_allow_html=True)
                        rows = [
                            ("↗ Growth Return", pct(summary["growth_return"])),
                            ("🔥 Inflation", pct(summary["inflation"])),
                            ("🛡️ Safe Return", pct(summary["safe_return"])),
                            ("🗓️ Bucket 1 Years", f"{summary['bucket1_years']:.1f}"),
                            ("↔ Roth Conversion", money(summary["annual_conversion"])),
                        ]

                        for label, value in rows:
                            st.markdown(
                                f"""
                                <div class="kv-row">
                                    <span class="kv-left">{label}</span>
                                    <span class="kv-right">{value}</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                    with right:
                        st.markdown("<div class='section-title'>Other Income Annual</div>", unsafe_allow_html=True)
                        st.markdown(
                            f"""
                            <div class="kv-row">
                                <span class="kv-left">Social Security</span>
                                <span class="kv-right">{money(summary['user_ss'] + summary['spouse_ss'])}</span>
                            </div>
                            <div class="kv-row">
                                <span class="kv-left">Other Income</span>
                                <span class="kv-right">{money(summary['simple_income'])}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        st.divider()
                        income_col, wr_col = st.columns(2)
                        income_col.metric("Income Coverage", pct(summary["income_coverage"]))
                        wr_col.metric("Max Withdrawal Rate", pct(summary["rough_wr"]))

                    with st.expander("AI Recommendations for This Scenario"):
                        st.caption("Educational only. These suggestions are not financial, tax, legal, insurance, or investment advice.")

                        st.markdown("**Quick rule-based suggestions**")
                        for rec in recommendations:
                            st.write(f"- {rec}")

                        st.divider()

                        ai_key = f"ai_recommendation_{sid}"

                        if st.button("Generate AI Recommendation", key=f"generate_ai_{sid}", use_container_width=True):
                            with st.spinner("Generating AI recommendation..."):
                                st.session_state.saved_ai_recommendations[ai_key] = generate_ai_recommendation_for_saved_scenario(
                                    scenario["scenario_name"],
                                    summary,
                                    recommendations
                                )

                        if ai_key in st.session_state.saved_ai_recommendations:
                            st.markdown("**AI-generated scenario review**")
                            st.markdown(st.session_state.saved_ai_recommendations[ai_key])

                            if st.button("Clear AI Recommendation", key=f"clear_ai_{sid}", use_container_width=True):
                                st.session_state.saved_ai_recommendations.pop(ai_key, None)
                                st.rerun()
                        else:
                            st.info("Click the button to generate a plain-English AI review for this saved scenario.")

                    b1, b2, b3, b4, b5 = st.columns([1, 1, 1, 1, 1])

                    with b1:
                        if st.button("↥ Load This Scenario", key=f"load_{sid}", use_container_width=True, type="primary"):
                            apply_scenario_data(data)
                            st.success("Scenario loaded.")
                            st.rerun()

                    with b2:
                        compare_label = "Remove Compare" if is_selected else "⚖ Compare"
                        if st.button(compare_label, key=f"compare_{sid}", use_container_width=True):
                            if is_selected:
                                st.session_state.compare_scenarios.pop(sid, None)
                            else:
                                st.session_state.compare_scenarios[sid] = {
                                    "name": scenario["scenario_name"],
                                    "data": data,
                                }
                            st.rerun()

                    with b3:
                        if st.button("⧉ Duplicate", key=f"duplicate_{sid}", use_container_width=True):
                            try:
                                copy_name = f"{scenario['scenario_name']} Copy"
                                save_scenario(user, copy_name, data)
                                st.success("Scenario duplicated.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Duplicate failed: {e}")

                    with b4:
                        pdf_bytes = build_pdf_report_bytes(
                            scenario["scenario_name"],
                            data,
                            summary,
                            recommendations
                        )
                        st.download_button(
                            "PDF Report",
                            data=pdf_bytes,
                            file_name=f"{scenario['scenario_name'].replace(' ', '_')}_report.pdf",
                            mime="application/pdf",
                            key=f"pdf_{sid}",
                            use_container_width=True
                        )

                    with b5:
                        confirm_key = f"confirm_delete_{sid}"

                        if st.session_state.get(confirm_key, False):
                            if st.button("Confirm Delete", key=f"confirm_delete_btn_{sid}", use_container_width=True):
                                try:
                                    supabase.table("retirement_scenarios").delete().eq("id", scenario["id"]).eq("user_id", user.id).execute()
                                    st.session_state.compare_scenarios.pop(sid, None)
                                    st.session_state[confirm_key] = False
                                    st.success("Scenario deleted.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Delete failed: {e}")

                            if st.button("Cancel", key=f"cancel_delete_btn_{sid}", use_container_width=True):
                                st.session_state[confirm_key] = False
                                st.rerun()
                        else:
                            if st.button("🗑 Delete", key=f"delete_{sid}", use_container_width=True):
                                st.session_state[confirm_key] = True
                                st.rerun()

            st.divider()

            t1, t2, t3, t4 = st.columns([1.2, 1, 1, 1])
            with t1:
                if st.button("＋ Create New Blank Scenario", use_container_width=True):
                    try:
                        save_scenario(user, "New Blank Scenario", blank_scenario_data())
                        st.success("Blank scenario created.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Blank scenario failed: {e}")

            with t2:
                if st.button("Conservative", use_container_width=True):
                    try:
                        save_scenario(user, "Conservative Plan", make_template_data("Conservative"))
                        st.success("Conservative scenario created.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Template failed: {e}")

            with t3:
                if st.button("Base", use_container_width=True):
                    try:
                        save_scenario(user, "Base Plan", make_template_data("Base"))
                        st.success("Base scenario created.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Template failed: {e}")

            with t4:
                if st.button("Aggressive", use_container_width=True):
                    try:
                        save_scenario(user, "Aggressive Plan", make_template_data("Aggressive"))
                        st.success("Aggressive scenario created.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Template failed: {e}")



with tabs[10]:
    st.header("Best Places to Retire")
    page_help(
        "Best Places to Retire",
        "Phase 1 compares states. Phase 2 adds personalized tax estimates. Phase 3 adds city/place recommendations. Phase 4 adds state comparison. Phase 5 adds a personalized location recommendation engine."
    )

    st.warning("Educational purposes only. State taxes, cost of living, healthcare access, and insurance costs change over time. Verify details before making relocation or tax decisions.")

    places_df = get_phase1_retirement_places_data()

    st.subheader("Phase 1 Retirement Location Ranking")

    c1, c2 = st.columns([1.2, 2.0])
    with c1:
        priority = st.selectbox(
            "What matters most?",
            [
                "Balanced overall",
                "Lowest taxes",
                "Lowest cost",
                "Healthcare access",
                "Lifestyle / weather",
            ],
            help="This changes the sort order. Phase 1 is a directional scoring model."
        )

    with c2:
        st.info(
            "Phase 1 is a static comparison. Phase 2 can estimate taxes based on the user's projected retirement income, Social Security, Roth withdrawals, and state choices."
        )

    ranked_df = filter_places_data(places_df, priority).reset_index(drop=True)
    ranked_df.insert(0, "Rank", ranked_df.index + 1)
    ranked_df["Fit Label"] = ranked_df["Overall Score"].map(score_badge)

    top = ranked_df.iloc[0]
    st.success(
        f"Top current match by **{priority}**: **{top['State']}** "
        f"with an overall score of **{int(top['Overall Score'])}/100**."
    )

    st.pyplot(plot_best_states_scores(ranked_df), use_container_width=True)

    st.subheader("State Comparison Table")

    display_cols = [
        "Rank",
        "State",
        "Overall Score",
        "Fit Label",
        "Tax Score",
        "Cost Score",
        "Healthcare Score",
        "Lifestyle Score",
        "Climate Score",
        "Example Places",
        "Best Fit",
    ]

    st.dataframe(
        ranked_df[display_cols],
        use_container_width=True,
        hide_index=True
    )

    st.subheader("State Details")

    selected_state = st.selectbox(
        "Choose a state to review",
        ranked_df["State"].tolist()
    )

    selected = ranked_df[ranked_df["State"] == selected_state].iloc[0]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Overall", f"{int(selected['Overall Score'])}/100", selected["Fit Label"])
    m2.metric("Taxes", f"{int(selected['Tax Score'])}/100")
    m3.metric("Cost", f"{int(selected['Cost Score'])}/100")
    m4.metric("Healthcare", f"{int(selected['Healthcare Score'])}/100")
    m5.metric("Lifestyle", f"{int(selected['Lifestyle Score'])}/100")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Why it ranks well")
        st.write(selected["Why It Ranks Well"])

        st.markdown("### Example places")
        st.write(selected["Example Places"])

    with c2:
        st.markdown("### Watch outs")
        st.write(selected["Watch Outs"])

        st.markdown("### Best fit")
        st.write(selected["Best Fit"])

    st.divider()

    st.subheader("Phase 2: Personalized Tax Estimate")
    st.write(
        "This estimates how each state may compare using your own retirement income and spending assumptions. "
        "It is simplified and educational, but it makes the location comparison feel much more personal."
    )

    default_ss = float(st.session_state.user_ss or 0)
    if st.session_state.has_spouse:
        default_ss += float(st.session_state.spouse_ss or 0)

    default_spending = annual_household_spending() + float(st.session_state.healthcare or 0)
    if st.session_state.has_spouse:
        default_spending += float(st.session_state.spouse_healthcare or 0)

    estimated_portfolio_need = max(default_spending - default_ss - float(st.session_state.simple_income or 0), 0)

    c1, c2, c3 = st.columns(3)
    ss_income = c1.number_input(
        "Annual Social Security income",
        min_value=0,
        value=int(default_ss),
        step=1000,
        help="Estimated annual household Social Security income."
    )
    pretax_withdrawals = c2.number_input(
        "Annual pre-tax withdrawals",
        min_value=0,
        value=int(estimated_portfolio_need),
        step=1000,
        help="Estimated annual withdrawals from traditional 401k/IRA accounts."
    )
    pension_other_income = c3.number_input(
        "Annual pension / other taxable income",
        min_value=0,
        value=int(st.session_state.simple_income or 0),
        step=1000,
        help="Pension, rental income, annuity income, side income, or other taxable income."
    )

    c1, c2, c3 = st.columns(3)
    taxable_income = c1.number_input(
        "Annual taxable brokerage income",
        min_value=0,
        value=0,
        step=1000,
        help="Estimated dividends, interest, or realized capital gains from taxable accounts."
    )
    annual_spending_input = c2.number_input(
        "Annual household spending",
        min_value=0,
        value=int(default_spending),
        step=1000,
        help="Used to estimate sales tax exposure. The model assumes a portion of spending is taxable."
    )
    home_value = c3.number_input(
        "Estimated home value",
        min_value=0,
        value=400000,
        step=25000,
        help="Used to estimate property tax by state."
    )

    personalized_df = build_personalized_places_table(
        places_df,
        ss_income=ss_income,
        pretax_withdrawals=pretax_withdrawals,
        pension_other_income=pension_other_income,
        taxable_income=taxable_income,
        annual_spending=annual_spending_input,
        home_value=home_value,
    )
    personalized_df.insert(0, "Personal Rank", personalized_df.index + 1)

    best_personal = personalized_df.iloc[0]
    st.success(
        f"Best personalized match: **{best_personal['State']}** "
        f"with an estimated annual state/local tax burden of **{money(best_personal['Estimated Annual Tax'])}**."
    )

    st.pyplot(plot_personalized_tax_burden(personalized_df), use_container_width=True)

    personal_display = personalized_df.copy()
    for col in ["Estimated Annual Tax", "Income Tax", "Property Tax", "Sales Tax"]:
        personal_display[col] = personal_display[col].map(money)
    personal_display["Effective Tax Rate"] = personal_display["Effective Tax Rate"].map(pct)

    st.dataframe(
        personal_display[
            [
                "Personal Rank",
                "State",
                "Personalized Score",
                "Estimated Annual Tax",
                "Income Tax",
                "Property Tax",
                "Sales Tax",
                "Effective Tax Rate",
                "Example Places",
                "Best Fit",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    with st.expander("How the Phase 2 estimate works"):
        st.write("""
This simplified model estimates:

- **State income tax** based on pre-tax withdrawals, pension/other income, and taxable brokerage income.
- **Property tax** based on the estimated home value and a directional state property-tax rate.
- **Sales tax** based on an assumed taxable portion of annual spending.
- **Personalized Score** using estimated tax drag plus cost, healthcare, lifestyle, and climate scores.

This is not a replacement for a CPA or tax-planning software. It is meant to help users identify which states are worth deeper research.
""")

    st.divider()

    st.subheader("Phase 3: City / Place-Level Recommendations")
    st.write(
        "This adds specific retirement places within the top states. Use it to compare lifestyle fit, healthcare, affordability, golf/recreation, and climate at a city/community level."
    )

    city_df = get_phase3_city_places_data()

    c1, c2 = st.columns(2)
    selected_states = c1.multiselect(
        "Filter by state",
        sorted(city_df["State"].unique().tolist()),
        default=[],
        help="Leave blank to include all states."
    )

    lifestyle_priority = c2.selectbox(
        "City lifestyle priority",
        [
            "Balanced city fit",
            "Golf / recreation",
            "Healthcare",
            "Lower cost",
            "Coastal / warm lifestyle",
            "Active adult community",
        ],
        help="This changes how places are sorted and filtered."
    )

    filtered_city_df = filter_city_places(city_df, selected_states, lifestyle_priority)

    if filtered_city_df.empty:
        st.warning("No city matches found for that filter. Try a broader lifestyle or fewer states.")
    else:
        filtered_city_df.insert(0, "City Rank", filtered_city_df.index + 1)

        best_city = filtered_city_df.iloc[0]
        st.success(
            f"Top place match: **{best_city['Place']}, {best_city['State']}** "
            f"with a city score of **{int(best_city['Overall City Score'])}/100**."
        )

        st.pyplot(plot_city_scores(filtered_city_df), use_container_width=True)

        st.dataframe(
            filtered_city_df[
                [
                    "City Rank",
                    "Place",
                    "State",
                    "Type",
                    "Overall City Score",
                    "Affordability",
                    "Healthcare",
                    "Lifestyle",
                    "Golf / Recreation",
                    "Climate",
                    "Why Retire Here",
                    "Watch Outs",
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Place Detail")

        selected_place_label = st.selectbox(
            "Choose a place to review",
            (filtered_city_df["Place"] + ", " + filtered_city_df["State"]).tolist()
        )

        selected_place = filtered_city_df[
            (filtered_city_df["Place"] + ", " + filtered_city_df["State"]) == selected_place_label
        ].iloc[0]

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("City Score", f"{int(selected_place['Overall City Score'])}/100")
        m2.metric("Affordability", f"{int(selected_place['Affordability'])}/100")
        m3.metric("Healthcare", f"{int(selected_place['Healthcare'])}/100")
        m4.metric("Lifestyle", f"{int(selected_place['Lifestyle'])}/100")
        m5.metric("Golf / Rec", f"{int(selected_place['Golf / Recreation'])}/100")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Why retire here")
            st.write(selected_place["Why Retire Here"])
            st.markdown("### Community type")
            st.write(selected_place["Type"])

        with c2:
            st.markdown("### Watch outs")
            st.write(selected_place["Watch Outs"])
            st.markdown("### Best next research step")
            st.write(
                "Compare housing prices, property taxes, insurance, healthcare networks, and lifestyle fit for this specific area."
            )

        city_csv = filtered_city_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download City Recommendations CSV",
            city_csv,
            "best_places_to_retire_phase3_cities.csv",
            "text/csv",
            use_container_width=True
        )

    st.divider()

    st.subheader("Phase 4: State-to-State Comparison")
    st.write(
        "Compare 2 to 4 states side by side using the base score, personalized score, estimated taxes, healthcare, lifestyle, cost, and watch-outs."
    )

    default_compare_states = ["Michigan", "Florida", "South Carolina"]
    available_states = sorted(places_df["State"].unique().tolist())

    compare_states = st.multiselect(
        "Choose states to compare",
        available_states,
        default=[s for s in default_compare_states if s in available_states],
        help="Pick 2 to 4 states for the cleanest comparison."
    )

    if len(compare_states) < 2:
        st.info("Choose at least 2 states to compare.")
    else:
        if len(compare_states) > 4:
            st.warning("For readability, only the first 4 selected states are shown.")
            compare_states = compare_states[:4]

        compare_df = build_state_comparison_table(
            places_df,
            personalized_df,
            compare_states
        )

        if compare_df.empty:
            st.warning("No comparison data found for the selected states.")
        else:
            st.success("State comparison generated.")

            for note in build_compare_narrative(compare_df):
                st.write(f"- {note}")

            st.pyplot(plot_state_comparison_scores(compare_df), use_container_width=True)
            st.pyplot(plot_state_tax_stack(compare_df), use_container_width=True)

            comparison_display = compare_df.copy()
            for col in ["Estimated Annual Tax", "Income Tax", "Property Tax", "Sales Tax"]:
                comparison_display[col] = comparison_display[col].map(money)
            comparison_display["Effective Tax Rate"] = comparison_display["Effective Tax Rate"].map(pct)

            st.subheader("Side-by-Side Comparison Table")
            st.dataframe(
                comparison_display[
                    [
                        "State",
                        "Overall Score",
                        "Personalized Score",
                        "Estimated Annual Tax",
                        "Income Tax",
                        "Property Tax",
                        "Sales Tax",
                        "Effective Tax Rate",
                        "Cost Score",
                        "Healthcare Score",
                        "Lifestyle Score",
                        "Climate Score",
                        "Example Places",
                        "Best Fit",
                        "Watch Outs",
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Plain-English Trade-Offs")

            for _, row in compare_df.iterrows():
                with st.expander(f"{row['State']} trade-off summary"):
                    st.write(f"**Best fit:** {row['Best Fit']}")
                    st.write(f"**Example places:** {row['Example Places']}")
                    st.write(f"**Estimated annual state/local tax:** {money(row['Estimated Annual Tax'])}")
                    st.write(f"**Watch-outs:** {row['Watch Outs']}")

            compare_csv = compare_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download State Comparison CSV",
                compare_csv,
                "state_to_state_retirement_comparison.csv",
                "text/csv",
                use_container_width=True
            )

    st.divider()

    st.subheader("Phase 5: Personalized Location Recommendation Engine")
    st.write(
        "This turns the location tool into a recommendation engine. Adjust what matters most, then the app ranks specific places using taxes, cost, healthcare, lifestyle, climate, and golf/recreation."
    )

    city_df_phase5 = get_phase3_city_places_data()

    st.markdown("### What matters most to you?")
    w1, w2, w3 = st.columns(3)
    tax_weight = w1.slider("Tax importance", 0, 10, 8, help="Higher means lower estimated taxes matter more.")
    cost_weight = w2.slider("Cost of living importance", 0, 10, 7, help="Higher means affordability matters more.")
    healthcare_weight = w3.slider("Healthcare importance", 0, 10, 8, help="Higher means healthcare access matters more.")

    w1, w2, w3 = st.columns(3)
    lifestyle_weight = w1.slider("Lifestyle importance", 0, 10, 8, help="Higher means restaurants, beach, mountains, walkability, and community matter more.")
    climate_weight = w2.slider("Climate importance", 0, 10, 7, help="Higher means weather and winter escape value matter more.")
    golf_weight = w3.slider("Golf / recreation importance", 0, 10, 7, help="Higher means golf and outdoor recreation matter more.")

    weights = calculate_location_fit_profile(
        tax_weight,
        cost_weight,
        healthcare_weight,
        lifestyle_weight,
        climate_weight,
        golf_weight,
    )

    c1, c2, c3 = st.columns(3)

    preferred_states = c1.multiselect(
        "Preferred states, optional",
        sorted(places_df["State"].unique().tolist()),
        default=[],
        help="These states get a small preference boost."
    )

    avoid_states = c2.multiselect(
        "States to avoid, optional",
        sorted(places_df["State"].unique().tolist()),
        default=[],
        help="These states will be removed from recommendations."
    )

    wants_snowbird = c3.checkbox(
        "Interested in snowbird strategy?",
        value=True,
        help="Adds weight to warm-weather winter destinations."
    )

    recommendation_df = build_retirement_location_recommendation_engine(
        city_df_phase5,
        personalized_df,
        weights,
        preferred_states=preferred_states,
        avoid_states=avoid_states,
        wants_snowbird=wants_snowbird,
    )

    if recommendation_df.empty:
        st.warning("No recommendations found. Try removing avoided states or broadening preferences.")
    else:
        top_location = recommendation_df.iloc[0]

        st.success(
            f"Top personalized recommendation: **{top_location['Place']}, {top_location['State']}** "
            f"with a fit score of **{int(top_location['Recommended Fit Score'])}/100**."
        )

        for note in build_location_recommendation_summary(recommendation_df):
            st.write(f"- {note}")

        st.pyplot(plot_location_engine_scores(recommendation_df), use_container_width=True)

        display_recs = recommendation_df.copy()
        display_recs["Estimated Annual State/Local Tax"] = display_recs["Estimated Annual State/Local Tax"].map(money)

        st.dataframe(
            display_recs[
                [
                    "Place",
                    "State",
                    "Type",
                    "Recommended Fit Score",
                    "Estimated Annual State/Local Tax",
                    "Healthcare",
                    "Affordability",
                    "Lifestyle",
                    "Climate",
                    "Golf / Recreation",
                    "Why It Fits",
                    "Watch Outs",
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Top Recommendation Detail")

        selected_location_label = st.selectbox(
            "Choose a recommended place",
            (recommendation_df["Place"] + ", " + recommendation_df["State"]).tolist(),
            key="phase5_location_detail"
        )

        selected_location = recommendation_df[
            (recommendation_df["Place"] + ", " + recommendation_df["State"]) == selected_location_label
        ].iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Fit Score", f"{int(selected_location['Recommended Fit Score'])}/100")
        m2.metric("Est. Annual Tax", money(selected_location["Estimated Annual State/Local Tax"]))
        m3.metric("Healthcare", f"{int(selected_location['Healthcare'])}/100")
        m4.metric("Golf / Rec", f"{int(selected_location['Golf / Recreation'])}/100")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Why it fits")
            st.write(selected_location["Why It Fits"])
            st.markdown("### Community type")
            st.write(selected_location["Type"])

        with c2:
            st.markdown("### Watch-outs")
            st.write(selected_location["Watch Outs"])
            st.markdown("### Next research step")
            st.write(
                "Look at housing costs, property taxes, insurance quotes, nearby hospitals, airport access, and whether you would rent before buying."
            )

        if wants_snowbird:
            st.subheader("Snowbird Strategy Ideas")
            snowbird_df = build_snowbird_recommendations(recommendation_df)

            if not snowbird_df.empty:
                snowbird_display = snowbird_df.head(5).copy()
                snowbird_display["Estimated Annual State/Local Tax"] = snowbird_display["Estimated Annual State/Local Tax"].map(money)

                st.dataframe(
                    snowbird_display[
                        [
                            "Place",
                            "State",
                            "Snowbird Fit Score",
                            "Estimated Annual State/Local Tax",
                            "Climate",
                            "Lifestyle",
                            "Golf / Recreation",
                            "Snowbird Strategy",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

                st.info(
                    "Snowbird idea: rent in the top warm-weather location for 1–3 winters before buying. "
                    "This protects flexibility and helps validate lifestyle fit."
                )

        rec_csv = recommendation_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Personalized Location Recommendations CSV",
            rec_csv,
            "personalized_retirement_location_recommendations.csv",
            "text/csv",
            use_container_width=True
        )

    st.divider()

    st.subheader("How to Read These Scores")
    st.write("""
- **Tax Score**: Directional estimate of state tax friendliness for retirees.
- **Cost Score**: Directional estimate of affordability and cost-of-living pressure.
- **Healthcare Score**: Directional estimate of healthcare access and retiree medical infrastructure.
- **Lifestyle Score**: Weather, recreation, golf/beach/mountain access, and retiree lifestyle.
- **Climate Score**: Weather comfort and snowbird appeal.
- **Overall Score**: Weighted blend of the above categories.
""")

    st.caption(
        "This app uses simplified educational scoring and tax-estimate logic, not a live tax engine. Verify tax laws, deductions, property taxes, insurance, and local costs before making relocation decisions."
    )

    csv = ranked_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Best Places CSV",
        csv,
        "best_places_to_retire_phase1.csv",
        "text/csv",
        use_container_width=True
    )


with tabs[11]:
    st.header("Monte Carlo Simulator")
    page_help(
        "Monte Carlo Simulator",
        "This page runs hundreds or thousands of randomized market-return paths to estimate how often the retirement plan survives. It helps show sequence-of-return risk and the range of possible ending portfolio balances."
    )

    if not can_run:
        st.info("Complete required inputs first.")
    else:
        st.warning("Educational estimate only. Monte Carlo results depend heavily on the return, volatility, inflation, and spending assumptions you enter.")

        st.subheader("Simulation Settings")

        c1, c2, c3, c4 = st.columns(4)

        num_simulations = c1.number_input(
            "Number of simulations",
            min_value=100,
            max_value=2000,
            value=500,
            step=100,
            help="More simulations give a smoother estimate, but may run slower."
        )

        mean_return = c2.slider(
            "Average annual return",
            min_value=0.0,
            max_value=12.0,
            value=float(st.session_state.growth_return) * 100,
            step=0.25,
            help="Expected average annual return for growth assets."
        ) / 100

        volatility = c3.slider(
            "Annual volatility",
            min_value=1.0,
            max_value=25.0,
            value=12.0,
            step=0.5,
            help="How much yearly returns vary. Higher volatility increases sequence risk."
        ) / 100

        seed = c4.number_input(
            "Random seed",
            min_value=1,
            max_value=99999,
            value=42,
            step=1,
            help="Keeps results repeatable. Change this to generate a different random set."
        )

        run_mc = st.button("Run Monte Carlo Simulation", type="primary", use_container_width=True)

        if run_mc:
            with st.spinner("Running Monte Carlo simulations..."):
                st.session_state.mc_result = run_monte_carlo_simulation(
                    int(num_simulations),
                    float(mean_return),
                    float(volatility),
                    int(seed)
                )

        if "mc_result" not in st.session_state:
            st.info("Click **Run Monte Carlo Simulation** to generate probability-of-success results.")
        else:
            mc = st.session_state.mc_result
            results_df = mc["results_df"]
            paths_df = mc["paths_df"]

            st.subheader("Monte Carlo Results")

            success_rate = mc["success_rate"]
            median_ending = mc["median_ending"]
            p10_ending = mc["p10_ending"]
            p90_ending = mc["p90_ending"]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Probability of Success", pct(success_rate))
            m2.metric("Median Ending Portfolio", money(median_ending))
            m3.metric("10th Percentile Ending", money(p10_ending))
            m4.metric("90th Percentile Ending", money(p90_ending))

            st.progress(success_rate)

            if success_rate >= 0.90:
                st.success("Monte Carlo result: Strong probability of success under these assumptions.")
            elif success_rate >= 0.75:
                st.warning("Monte Carlo result: Moderate-to-good probability of success. Stress testing is still recommended.")
            elif success_rate >= 0.60:
                st.warning("Monte Carlo result: Borderline. Consider reducing spending, delaying retirement, or improving income coverage.")
            else:
                st.error("Monte Carlo result: High risk. The plan fails in many simulated market paths.")

            st.caption(
                "Success means the plan reaches the final planning age with money remaining and no unmet spending years."
            )

            st.subheader("Portfolio Path Range")
            st.pyplot(plot_monte_carlo_paths(paths_df, results_df), use_container_width=True)

            st.subheader("Ending Portfolio Distribution")
            st.pyplot(plot_monte_carlo_ending_distribution(results_df), use_container_width=True)

            st.subheader("Simulation Detail")

            detail = results_df.copy()
            detail["Success"] = detail["Success"].map(lambda x: "Success" if x else "Failed")
            detail["Ending Portfolio"] = detail["Ending Portfolio"].map(money)
            detail["Max Withdrawal Rate"] = detail["Max Withdrawal Rate"].map(pct)
            detail["Average Return"] = detail["Average Return"].map(pct)
            detail["Worst Year Return"] = detail["Worst Year Return"].map(pct)
            st.dataframe(detail.head(100), use_container_width=True, hide_index=True)

            csv = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Monte Carlo CSV",
                csv,
                "monte_carlo_results.csv",
                "text/csv",
                use_container_width=True
            )




with tabs[12]:
    st.header("Stress Tests")

    if not can_run:
        st.info("Complete required inputs first.")
    else:
        st.warning("Stress tests simulate difficult retirement conditions.")

        if st.button("Run Stress Tests", type="primary", use_container_width=True):
            if "stress_results_df" in st.session_state:
                del st.session_state.stress_results_df

            years = int(st.session_state.end_age) - int(st.session_state.current_age) + 1
            base_return = float(st.session_state.growth_return)

            stress_results = []

            stress_results.append(
                run_stress_test_scenario(
                    "Base Case",
                    forced_returns=[base_return] * years
                )
            )

            stress_results.append(
                run_stress_test_scenario(
                    "Bad First 3 Years",
                    forced_returns=[-0.20, -0.12, -0.08] + [base_return] * (years - 3)
                )
            )

            stress_results.append(
                run_stress_test_scenario(
                    "High Inflation",
                    inflation_override=0.06
                )
            )

            stress_results.append(
                run_stress_test_scenario(
                    "4% Returns",
                    forced_returns=[0.04] * years
                )
            )

            stress_results.append(
                run_stress_test_scenario(
                    "Healthcare Shock",
                    spending_multiplier=1.15
                )
            )

            stress_results.append(
                run_stress_test_scenario(
                    "Severe Recession",
                    forced_returns=[-0.30, -0.15, 0.00, 0.03] + [base_return] * (years - 4)
                )
            )

            st.session_state.stress_results_df = pd.DataFrame(stress_results)

        if "stress_results_df" in st.session_state:

            stress_df = st.session_state.stress_results_df.copy()

            # Safety: older cached stress-test results may not include these new columns.
            if "Lasts Until Age" not in stress_df.columns:
                stress_df["Lasts Until Age"] = int(st.session_state.end_age)
            if "Years Covered" not in stress_df.columns:
                stress_df["Years Covered"] = stress_df["Lasts Until Age"].astype(int) - int(st.session_state.current_age)

            st.subheader("Stress Test Summary")
            st.pyplot(plot_stress_test_chart(stress_df), use_container_width=True)

            display_df = stress_df.copy()

            display_df["Lasts Until Age"] = display_df["Lasts Until Age"].map(lambda x: int(x))
            display_df["Years Covered"] = display_df["Years Covered"].map(lambda x: max(int(x), 0))
            display_df["Ending Portfolio"] = display_df["Ending Portfolio"].map(money)
            display_df["Max Withdrawal Rate"] = display_df["Max Withdrawal Rate"].map(pct)
            display_df["Income Coverage"] = display_df["Income Coverage"].map(pct)

            st.caption("Lasts Until Age shows the first age where the plan fails, or the final plan age if it survives.")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.markdown("""
### Stress Test Definitions

- **Base Case** → Uses your normal assumptions.
- **Bad First 3 Years** → Simulates retiring into a bear market.
- **High Inflation** → Uses 6% inflation.
- **4% Returns** → Assumes weaker long-term market returns.
- **Healthcare Shock** → Increases spending by 15%.
- **Severe Recession** → Simulates a major market crash and slow recovery.
""")



with tabs[13]:
    st.header("PDF Report")
    page_help(
        "PDF Report",
        "This page exports a visually polished retirement report with the plan summary, assumptions, dashboard charts, recommendations, Monte Carlo results, stress tests, and a projection snapshot."
    )

    if not can_run:
        st.info("Complete required inputs first.")
    else:
        st.success("Ready to export a professional-looking retirement report.")
        st.warning("Educational purposes only. This report is not financial, tax, legal, insurance, or investment advice.")

        st.write("""
The PDF report includes:

- RTV score and executive summary
- Key planning assumptions
- Portfolio, spending, income, and withdrawal charts
- Possible recommendations and planning observations
- Recommended actions to improve the score
- Spend-more analysis
- Monte Carlo results, if already run
- Stress test results, if already run
- Projection snapshot
""")

        if "mc_result" not in st.session_state:
            st.warning("Monte Carlo has not been run yet. The PDF will include a placeholder for that section.")

        if "stress_results_df" not in st.session_state:
            st.warning("Stress tests have not been run yet. The PDF will include a placeholder for that section.")

        if st.button("Generate PDF Report", type="primary", use_container_width=True):
            with st.spinner("Creating report..."):
                st.session_state.pdf_report_bytes = build_pdf_report(df)

        if "pdf_report_bytes" in st.session_state:
            st.download_button(
                "Download Retirement Report PDF",
                data=st.session_state.pdf_report_bytes,
                file_name="retirement_readiness_report.pdf",
                mime="application/pdf",
                use_container_width=True
            )


with tabs[14]:
    st.header("AI Retirement Coach")
    page_help(
        "AI Retirement Coach",
        "This chat explains the retirement numbers in plain English. It uses your current plan context, but it is educational only and not financial, tax, legal, insurance, or investment advice."
    )
    st.warning("Educational use only. This chat does not provide financial, tax, legal, insurance, or investment advice.")

    try:
        from openai import OpenAI
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            st.info("Add your OpenAI API key in Streamlit Secrets to enable chat.")
            st.code('OPENAI_API_KEY = "your-api-key-here"', language="toml")
            st.stop()
        client = OpenAI(api_key=api_key)
    except Exception:
        st.error("OpenAI is not configured. Add OPENAI_API_KEY in Streamlit Secrets and openai in requirements.txt.")
        st.stop()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if st.button("Clear chat"):
        st.session_state.chat_messages = []
        st.rerun()

    if can_run and not df.empty:
        rtv_score, rtv_label, rtv_reasons = calculate_rtv_score(df)

        plan_context = f"""
        Current age: {st.session_state.current_age}
        Retirement age: {st.session_state.retire_age}
        Plan-through age: {st.session_state.end_age}
        Traditional: {st.session_state.traditional}
        Roth: {st.session_state.roth}
        Taxable: {st.session_state.taxable}
        Bucket 1: {st.session_state.cash}
        Annual spending before healthcare: {annual_household_spending()}
        Spending target finder available: Yes
        Spending change enabled: {st.session_state.enable_spending_change}
        Spending change age: {st.session_state.spending_change_age}
        New monthly spending after change age: {st.session_state.spending_change_monthly}
        Total other income across plan: {df["Total Other Income"].sum()}
        Average income coverage: {df["Income Coverage Ratio"].mean()}
        Ending portfolio: {df["End Total"].iloc[-1]}
        Max withdrawal rate: {df["Withdrawal Rate"].max()}
        RTV Score: {rtv_score}/100
        RTV Label: {rtv_label}
        RTV Reasons: {", ".join(rtv_reasons)}
        """
    else:
        plan_context = "The user has not completed the retirement inputs yet."

    system_prompt = f"""
    You are an educational retirement planning assistant inside a calculator.
    You are not a financial advisor, CPA, attorney, or insurance agent.
    Use the model numbers when available. Do not invent missing values.
    Focus on retirement timing, spending, other income, income gaps, Roth conversions,
    Social Security, Bucket 1, sequence risk, spouse/survivor planning, and the RTV score.
    RTV means Retirement Timing Viability.
    Important: Do not over-penalize a plan for low outside-income coverage or a high one-year withdrawal rate
    if the full projection ends with a large portfolio balance and no unmet spending needs.
    Ending balance and plan survivability are the primary success signals.

    Plan context:
    {plan_context}
    """

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    with st.form("ai_chat_form", clear_on_submit=True):
        question = st.text_area(
            "Ask your retirement coach a question",
            placeholder="Example: Can I retire at 58? Should I take Social Security at 62 or 67? How can I improve my RTV score?",
            height=90,
            key="ai_question_box"
        )
        send_question = st.form_submit_button("Send question")

    if send_question and question.strip():
        clean_question = question.strip()
        st.session_state.chat_messages.append({"role": "user", "content": clean_question})

        with st.chat_message("user"):
            st.markdown(clean_question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = client.responses.create(
                        model="gpt-4.1-mini",
                        input=[{"role": "system", "content": system_prompt}, *st.session_state.chat_messages],
                        max_output_tokens=900,
                    )
                    answer = response.output_text
                except Exception as e:
                    answer = f"Chat error: {e}"

                st.markdown(answer)

        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        st.rerun()

    elif send_question and not question.strip():
        st.warning("Type a question first, then tap Send question.")

with tabs[15]:
    st.header("How to Use This")
    page_help(
        "Help / Instructions",
        "This page explains how to move through the app, what the major terms mean, and how to interpret the results."
    )

    st.subheader("Key Terms")
    terms = pd.DataFrame([
        ["RTV Score", "Retirement Timing Viability. A 0–100 score estimating whether the selected retirement age appears sustainable under the current assumptions."],
        ["Portfolio at Retirement", "The projected investment balance when retirement begins."],
        ["End of Plan Portfolio", "The projected balance left at the final age selected in the plan."],
        ["Max Withdrawal Rate", "The highest annual portfolio withdrawal divided by portfolio balance in the projection."],
        ["Income Coverage", "How much of annual spending is covered by non-portfolio income such as Social Security, pension, or other income."],
        ["Bucket 1", "Safer money intended to cover near-term retirement spending and reduce sequence-of-return risk."],
        ["Roth Conversion", "Moving money from traditional pre-tax accounts to Roth accounts. This may create taxes today but can reduce future tax exposure."],
        ["Unmet Need", "Spending need that the plan could not cover in a projected year. Any unmet need is a major warning sign."],
    ], columns=["Term", "Meaning"])
    st.dataframe(terms, use_container_width=True, hide_index=True)

    st.subheader("How to Interpret Results")
    st.write("""
- **Very Strong / Strong:** The projection survives with a healthy cushion.
- **Likely Viable:** The plan appears workable, but should be stress-tested.
- **Needs Optimization:** The plan may work, but improving spending, retirement age, income, or contributions could help.
- **High Risk:** The plan may deplete assets or leave too little margin.
""")

    st.write("""
1. Complete **Guided Questions**.
2. Complete **Budget Builder** using either a flat monthly number or detailed budget.
3. Complete **Income Builder** using either simple income or advanced income sources.
4. Complete **Spouse / Partner Questions** only if applicable.
5. Review answers, then check the dashboard and recommendations.
6. Use **Saved Scenarios** to save, reload, and compare planning versions.
7. Use RTV, Retirement Timing Viability, as a quick confidence score for your retirement timing.
8. Add home and mortgage information to evaluate home equity, mortgage cash flow, downsizing, relocation, and housing flexibility.
9. Use planned spending changes when retirement spending will change at a future age, such as higher travel spending early and lower spending later.
10. Use the Spending Target Finder to estimate a monthly spending level that may improve or maintain your RTV score.
8. Use **Best Places to Retire** to compare retirement-friendly states and cities by taxes, cost of living, healthcare, lifestyle, climate, and recreation.
9. Use **Monte Carlo** to estimate probability of success across randomized market paths.

Income examples:
- pension
- part-time work
- consulting
- rental income
- annuity
- business income
- dividends
- royalties
- trust income

All defaults start at zero so this can be shared with anyone.
""")
    st.warning("Educational planning tool only. Not financial, tax, legal, investment, or insurance advice.")
