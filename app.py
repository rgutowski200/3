import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
from datetime import datetime

st.set_page_config(page_title="Retirement Blueprint 101", layout="wide")

# ------------------------------------------------------------
# Clean build marker
# ------------------------------------------------------------
BUILD_LABEL = "Readiness Meter v1"

# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1220px;}
    [data-testid="stSidebar"] {background: linear-gradient(180deg, #061A3A 0%, #081F45 100%);} 
    [data-testid="stSidebar"] * {color: white !important;}
    [data-testid="stSidebar"] input {color: #111827 !important; background: white !important;}
    [data-testid="stSidebar"] .stSlider div[data-baseweb="slider"] * {color: white !important;}
    .metric-card {
        background: #ffffff;
        border: 1px solid #e6eaf0;
        border-radius: 18px;
        padding: 22px;
        min-height: 160px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
    }
    .metric-label {font-size: 0.92rem; font-weight: 700; color: #111827; margin-bottom: 18px;}
    .metric-value {font-size: 2.2rem; font-weight: 800; color: #111827; line-height: 1.1;}
    .metric-note {font-size: 0.9rem; color: #64748b; margin-top: 10px;}
    .green {color: #159947 !important; font-weight: 800;}
    .soft-box {
        background: #eef6ff;
        border: 1px solid #d7eafe;
        border-radius: 14px;
        padding: 16px 20px;
        color: #075985;
    }
    .success-box {
        background: #e9f9ef;
        border: 1px solid #c8f0d4;
        border-radius: 14px;
        padding: 16px 20px;
        color: #166534;
    }
    .warn-box {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-radius: 14px;
        padding: 16px 20px;
        color: #9a3412;
    }
    .section-title {font-size: 1.35rem; font-weight: 800; margin-top: 1.3rem; margin-bottom: 0.6rem;}
    .small-muted {color:#64748b; font-size:0.9rem;}
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e6eaf0;
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Session defaults
# ------------------------------------------------------------
def init_state():
    defaults = {
        "nav": "Dashboard",
        "premium_demo": True,
        "plan_name": "Base Plan",
        "name": "John",
        "age": 55,
        "retire_age": 58,
        "plan_age": 90,
        "current_income": 140000,
        "monthly_spending": 10400,
        "other_income": 6000,
        "pension_income": 0,
        "social_security": 24000,
        "ss_start_age": 62,
        "ss_fra_age": 67,
        "portfolio": 850000,
        "traditional": 680000,
        "roth": 110000,
        "taxable_cash": 60000,
        "hsa_balance": 0,
        "rule55_eligible": True,
        "aca_sensitive": True,
        "rmd_concern": "Medium",
        "market_downturn": False,
        "bucket1_balance": 450000,
        "bucket2_balance": 400000,
        "bucket1_return": 4.5,
        "bucket2_return": 8.0,
        "bucket1_years": 3,
        "home_equity": 300000,
        "home_value": 450000,
        "mortgage": 150000,
        "healthcare_monthly": 1000,
        "inflation": 3.0,
        "growth_return": 7.0,
        "safe_return": 4.5,
        "tax_rate": 18.0,
        "roth_conversion": 0,
        "aca_target_income": 60000,
        "filing_status": "Married Filing Jointly",
        "tax_year": "2026",
        "state_tax_rate": 4.25,
        "taxable_ss_percent": 85.0,
        "other_taxable_income": 0,
        "itemized_deductions": 0,
        "use_itemized": False,
        "spouse_enabled": False,
        "spouse_age": 53,
        "spouse_income": 0,
        "spouse_ss": 24000,
        "spouse_ss_start_age": 62,
        "spouse_ss_fra_age": 67,
        "phase2_compare_ages": [58, 62, 65, 67],
        "sidebar_age": 55,
        "sidebar_retire_age": 58,
        "sidebar_monthly_spending": 10400,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
if "saved_plans" not in st.session_state:
    st.session_state.saved_plans = []

# Keys included when saving/exporting/loading a local plan.
PLAN_INPUT_KEYS = [
    "plan_name", "name", "age", "retire_age", "plan_age",
    "current_income", "monthly_spending", "other_income", "pension_income",
    "social_security", "ss_start_age", "ss_fra_age", "portfolio", "traditional", "roth",
    "taxable_cash", "hsa_balance", "rule55_eligible", "aca_sensitive", "rmd_concern", "market_downturn", "bucket1_balance", "bucket2_balance", "bucket1_return",
    "bucket2_return", "bucket1_years", "home_equity", "home_value", "mortgage",
    "healthcare_monthly", "inflation", "growth_return", "safe_return",
    "tax_rate", "roth_conversion", "aca_target_income",
    "filing_status", "tax_year", "state_tax_rate", "taxable_ss_percent", "other_taxable_income", "itemized_deductions", "use_itemized",
    "spouse_enabled", "spouse_age", "spouse_income", "spouse_ss", "spouse_ss_start_age", "spouse_ss_fra_age",
    "phase2_compare_ages", "sidebar_age", "sidebar_retire_age", "sidebar_monthly_spending",
    "p5_plan_name", "p5_tags", "p5_notes",
]


def capture_plan_inputs():
    return {k: st.session_state.get(k) for k in PLAN_INPUT_KEYS if k in st.session_state}


def apply_plan_inputs(inputs):
    if not isinstance(inputs, dict):
        return
    for k, v in inputs.items():
        if k in PLAN_INPUT_KEYS:
            st.session_state[k] = v
    if "age" in inputs:
        st.session_state["sidebar_age"] = inputs.get("age")
    if "retire_age" in inputs:
        st.session_state["sidebar_retire_age"] = inputs.get("retire_age")
    if "monthly_spending" in inputs:
        st.session_state["sidebar_monthly_spending"] = inputs.get("monthly_spending")


def load_saved_plan(index):
    plan = st.session_state.saved_plans[index]
    inputs = plan.get("inputs", {})
    if inputs:
        apply_plan_inputs(inputs)
    else:
        # Backward-compatible fallback for older in-session saved plans.
        st.session_state["retire_age"] = int(plan.get("retirement_age", st.session_state.retire_age))
        st.session_state["plan_age"] = int(plan.get("planning_horizon", st.session_state.plan_age))
        st.session_state["monthly_spending"] = float(plan.get("annual_spending", annual_spending())) / 12
        st.session_state["portfolio"] = float(plan.get("portfolio", st.session_state.portfolio))
        st.session_state["home_equity"] = float(plan.get("home_equity", st.session_state.home_equity))
    st.session_state["last_loaded_plan"] = plan.get("plan_name", "Saved Plan")


def delete_saved_plan(index):
    if 0 <= index < len(st.session_state.saved_plans):
        st.session_state.saved_plans.pop(index)


def import_plan_payload(payload):
    if isinstance(payload, dict) and "saved_plans" in payload:
        imported = payload.get("saved_plans", [])
        if isinstance(imported, list):
            st.session_state.saved_plans.extend(imported)
            st.session_state["last_import_status"] = f"Imported {len(imported)} saved plan(s)."
    elif isinstance(payload, dict):
        st.session_state.saved_plans.append(payload)
        if payload.get("inputs"):
            apply_plan_inputs(payload["inputs"])
        st.session_state["last_import_status"] = "Imported 1 plan."
    else:
        st.session_state["last_import_status"] = "Import failed: unsupported file format."

# ------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------
def money(x):
    return f"${float(x):,.0f}"


def pct(x):
    return f"{float(x):.0f}%"


def section_guide(title, how_to_use, what_it_tells_you, tips=None):
    """Reusable guidance box for each major app section."""
    with st.expander(f"ℹ️ How to use this section — {title}", expanded=False):
        st.markdown("**How to use it**")
        st.markdown(how_to_use)
        st.markdown("**What it tells you**")
        st.markdown(what_it_tells_you)
        if tips:
            st.markdown("**Tips**")
            st.markdown(tips)


def annual_spending():
    return float(st.session_state.monthly_spending) * 12


def ss_claiming_factor(claim_age, fra_age=67):
    """Approximate Social Security claiming adjustment relative to full retirement age.

    Uses SSA's common reduction/credit rules: early filing reduces benefits by
    5/9 of 1% per month for the first 36 months before FRA, then 5/12 of 1%
    per month beyond that. Delaying after FRA earns about 2/3 of 1% per month,
    up to age 70.
    """
    claim_age = float(claim_age)
    fra_age = float(fra_age)
    if claim_age < fra_age:
        months_early = round((fra_age - claim_age) * 12)
        first_band = min(months_early, 36) * (5 / 9 / 100)
        second_band = max(0, months_early - 36) * (5 / 12 / 100)
        return max(0.0, 1 - first_band - second_band)
    months_delayed = round((min(claim_age, 70) - fra_age) * 12)
    return 1 + months_delayed * (2 / 3 / 100)


def adjusted_user_social_security():
    base = float(st.session_state.get("social_security", 0))
    return base * ss_claiming_factor(st.session_state.get("ss_start_age", 62), st.session_state.get("ss_fra_age", 67))


def adjusted_spouse_social_security():
    if not st.session_state.get("spouse_enabled", False):
        return 0.0
    base = float(st.session_state.get("spouse_ss", 0))
    return base * ss_claiming_factor(st.session_state.get("spouse_ss_start_age", 62), st.session_state.get("spouse_ss_fra_age", 67))


def guaranteed_income():
    spouse = adjusted_spouse_social_security()
    return adjusted_user_social_security() + float(st.session_state.pension_income) + float(st.session_state.other_income) + float(spouse)


def portfolio_total():
    return float(st.session_state.traditional) + float(st.session_state.roth) + float(st.session_state.taxable_cash)


def bucket_total():
    return float(st.session_state.get("bucket1_balance", 0)) + float(st.session_state.get("bucket2_balance", 0))


def bucket_blended_return():
    total = bucket_total()
    if total <= 0:
        return float(st.session_state.get("growth_return", 7.0))
    b1 = float(st.session_state.get("bucket1_balance", 0))
    b2 = float(st.session_state.get("bucket2_balance", 0))
    r1 = float(st.session_state.get("bucket1_return", 4.5))
    r2 = float(st.session_state.get("bucket2_return", 8.0))
    return ((b1 * r1) + (b2 * r2)) / total


def auto_bucket_split():
    total = portfolio_total()
    target_b1 = min(total, annual_spending() * float(st.session_state.get("bucket1_years", 3)))
    st.session_state.bucket1_balance = round(target_b1, 0)
    st.session_state.bucket2_balance = round(max(0, total - target_b1), 0)


def project_two_bucket(retire_age=None, plan_age=None):
    age = int(st.session_state.age)
    retire_age = int(retire_age if retire_age is not None else st.session_state.retire_age)
    plan_age = int(plan_age if plan_age is not None else st.session_state.plan_age)
    b1 = float(st.session_state.get("bucket1_balance", 0))
    b2 = float(st.session_state.get("bucket2_balance", 0))
    r1 = float(st.session_state.get("bucket1_return", 4.5)) / 100
    r2 = float(st.session_state.get("bucket2_return", 8.0)) / 100
    spend = annual_spending()
    income = guaranteed_income()
    rows = []
    for a in range(age, plan_age + 1):
        withdrawal = 0
        transfer_to_bucket1 = 0
        if a < retire_age:
            b1 = b1 * (1 + r1)
            b2 = b2 * (1 + r2)
        else:
            withdrawal = max(0, spend - income)
            b1 = b1 * (1 + r1)
            b2 = b2 * (1 + r2)
            if b1 < withdrawal and b2 > 0:
                transfer_to_bucket1 = min(b2, max(0, annual_spending() * float(st.session_state.get("bucket1_years", 3)) - b1))
                b2 -= transfer_to_bucket1
                b1 += transfer_to_bucket1
            draw_from_b1 = min(b1, withdrawal)
            b1 -= draw_from_b1
            remaining = max(0, withdrawal - draw_from_b1)
            if remaining > 0:
                b2 = max(0, b2 - remaining)
        rows.append({
            "Age": a,
            "Bucket 1": b1,
            "Bucket 2": b2,
            "Total Portfolio": b1 + b2,
            "Annual Withdrawal": withdrawal,
            "Transfer to Bucket 1": transfer_to_bucket1,
        })
    return pd.DataFrame(rows)


def readiness_score():
    spend = max(annual_spending(), 1)
    income_coverage = min(100, guaranteed_income() / spend * 100)
    portfolio_income = portfolio_total() * 0.04
    portfolio_coverage = min(100, portfolio_income / max(spend - guaranteed_income(), 1) * 100) if spend > guaranteed_income() else 100
    timing_bonus = max(0, min(20, (st.session_state.retire_age - st.session_state.age) * 4))
    score = 0.42 * income_coverage + 0.42 * portfolio_coverage + timing_bonus
    return int(max(0, min(100, score)))


def confidence_label(score):
    if score >= 80:
        return "High"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Needs Review"
    return "Low"


def project_portfolio(retire_age=None, return_rate=None, plan_age=None):
    age = int(st.session_state.age)
    retire_age = int(retire_age if retire_age is not None else st.session_state.retire_age)
    plan_age = int(plan_age if plan_age is not None else st.session_state.plan_age)
    r = float(return_rate if return_rate is not None else st.session_state.growth_return) / 100
    portfolio = portfolio_total()
    spend = annual_spending()
    income = guaranteed_income()
    rows = []
    for a in range(age, plan_age + 1):
        if a < retire_age:
            portfolio = portfolio * (1 + r)
            withdrawal = 0
        else:
            withdrawal = max(0, spend - income)
            portfolio = max(0, portfolio * (1 + r) - withdrawal)
        rows.append({"Age": a, "Portfolio": portfolio, "Withdrawal": withdrawal})
    return pd.DataFrame(rows)



def readiness_meter(score):
    """Return a Plotly gauge for the dashboard readiness score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=int(score),
        number={"suffix": "/100", "font": {"size": 34}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
            "bar": {"color": "#159947"},
            "bgcolor": "white",
            "borderwidth": 1,
            "bordercolor": "#e5e7eb",
            "steps": [
                {"range": [0, 40], "color": "#fee2e2"},
                {"range": [40, 60], "color": "#ffedd5"},
                {"range": [60, 80], "color": "#fef9c3"},
                {"range": [80, 100], "color": "#dcfce7"},
            ],
            "threshold": {
                "line": {"color": "#111827", "width": 3},
                "thickness": 0.75,
                "value": int(score),
            },
        },
        title={"text": "", "font": {"size": 14}},
    ))
    fig.update_layout(
        height=230,
        margin=dict(l=20, r=20, t=15, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#111827"},
    )
    return fig

def dashboard_chart():
    df = project_portfolio()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Age"], y=df["Portfolio"], mode="lines", name="Portfolio", line=dict(width=3)))
    fig.add_vline(x=st.session_state.retire_age, line_dash="dash", annotation_text="Retire")
    fig.add_vline(x=st.session_state.ss_start_age, line_dash="dot", annotation_text="Social Security")
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10), yaxis_tickprefix="$", yaxis_title="Portfolio", xaxis_title="Age")
    return fig

# ------------------------------------------------------------
# Input sync helpers
# ------------------------------------------------------------
def sync_from_sidebar():
    st.session_state.age = int(st.session_state.sidebar_age)
    st.session_state.retire_age = int(st.session_state.sidebar_retire_age)
    st.session_state.monthly_spending = int(st.session_state.sidebar_monthly_spending)


def apply_household_updates():
    st.session_state.age = int(st.session_state.phase1_age)
    st.session_state.retire_age = int(st.session_state.phase1_retire_age)
    st.session_state.sidebar_age = int(st.session_state.phase1_age)
    st.session_state.sidebar_retire_age = int(st.session_state.phase1_retire_age)


def apply_spending_updates():
    st.session_state.monthly_spending = int(st.session_state.phase1_monthly_spending)
    st.session_state.sidebar_monthly_spending = int(st.session_state.phase1_monthly_spending)

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📈 RETIREMENT")
    st.markdown("### BLUEPRINT 101")
    st.divider()

    nav = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Phase 1 — Foundation",
            "Phase 2 — Retirement Lab",
            "Phase 3 — Income & Tax",
            "Phase 4 — Lifestyle",
            "Phase 5 — My Plans",
            "Reports",
            "AI Coach",
            "Resources",
        ],
        key="nav",
    )

    st.divider()
    st.toggle("Premium demo unlocked", key="premium_demo")
    if st.session_state.premium_demo:
        st.success("Premium unlocked")
    else:
        st.info("Free dashboard mode")

    st.divider()
    st.markdown("### Quick Assumptions")
    st.text_input("Plan name", key="plan_name", help="Give this retirement scenario a name, such as Base Plan, Retire at 60, or Snowbird Plan.")
    st.number_input("Your age", min_value=45, max_value=90, key="sidebar_age", step=1, on_change=sync_from_sidebar, help="Your current age today. This drives retirement timing, growth years, Social Security timing, and Medicare bridge years.")
    st.slider("Target retirement age", 50, 75, key="sidebar_retire_age", on_change=sync_from_sidebar, help="The age you hope to stop full-time work and begin relying on retirement income.")
    st.number_input("Estimated monthly spend", min_value=0, step=500, key="sidebar_monthly_spending", on_change=sync_from_sidebar, help="Your estimated average monthly retirement spending. Use a quick estimate here; Phase 1 has a detailed budget builder.")
    st.caption("Build: Auto-save inputs v1")
    st.caption(f"Build: {BUILD_LABEL}")

# ------------------------------------------------------------
# Pages
# ------------------------------------------------------------
def show_dashboard():
    score = readiness_score()
    confidence = confidence_label(score)
    monthly_income = (guaranteed_income() + portfolio_total() * 0.04) / 12
    coverage = min(100, monthly_income / max(st.session_state.monthly_spending, 1) * 100)

    st.title(f"Good morning, {st.session_state.name}!")
    st.write("Here’s your retirement readiness overview.")
    section_guide(
        "Dashboard",
        "Use this page as your quick command center. Review the scorecards first, then use the timeline chart and next steps to decide which phase needs attention.",
        "It summarizes your current retirement picture: readiness score, projected retirement age, estimated monthly retirement income, confidence level, bridge years before Medicare, annual spending, and total portfolio.",
        "If something looks off, start in Phase 1 to clean up inputs. If the score is lower than expected, use Phase 2 and Phase 3 to test retirement age, returns, withdrawal order, and taxes."
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div class='metric-label'>Retirement Readiness Score</div>", unsafe_allow_html=True)
        st.plotly_chart(readiness_meter(score), use_container_width=True, config={"displayModeBar": False})
        st.markdown(f"<div class='green'>{confidence}</div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-note'>Based on income coverage, portfolio strength, spending, and retirement timing.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Projected Retirement Age</div>
            <div class='metric-value'>{st.session_state.retire_age}</div>
            <div class='green'>Optimal Range: 58–63</div>
            <div class='metric-note'>Adjust in Phase 1 or test alternate ages in Phase 2.</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Monthly Retirement Income</div>
            <div class='metric-value'>{money(monthly_income)}</div>
            <div class='green'>{coverage:.0f}% of target spending</div>
            <div class='metric-note'>Includes Social Security, other income, and a simple 4% portfolio estimate.</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Confidence Level</div>
            <div class='metric-value'>{confidence}</div>
            <div class='metric-note'>Your plan gets stronger as you add more detail in each phase.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Your Retirement Timeline")
    st.plotly_chart(dashboard_chart(), use_container_width=True)

    a, b, c = st.columns(3)
    a.metric("Bridge Years Before Medicare", max(0, 65 - st.session_state.retire_age))
    b.metric("Estimated Annual Spending", money(annual_spending()))
    c.metric("Portfolio Total", money(portfolio_total()))

    st.markdown("### Your Next Steps")
    st.write("1. Complete Phase 1 inputs.  2. Compare retirement ages in Phase 2.  3. Test income and tax strategy in Phase 3.  4. Compare lifestyle locations in Phase 4.  5. Save your best blueprint in Phase 5.")


def show_phase1():
    st.title("Phase 1 — Financial Foundation")
    st.write("Build the base retirement picture: income, spending, assets, debt, Social Security, and optional spouse planning.")
    section_guide(
        "Phase 1 — Financial Foundation",
        "Enter the core facts about your household: age, target retirement age, income, spending, Social Security, assets, debt, and spouse/partner information if applicable. Use rough numbers at first, then come back later with more detail.",
        "This phase creates the baseline used by the entire app. The dashboard, Retirement Lab, Income & Tax section, Lifestyle engine, My Plans, and Reports all pull from these inputs.",
        "Best practice: start simple, then improve accuracy over time. Spending and Social Security are usually the two fields that most change the output."
    )
    st.markdown("<div class='soft-box'>Free users can enter basic estimates. Premium users can go deeper with category spending, other income sources, spouse planning, and Social Security assumptions.</div>", unsafe_allow_html=True)

    tabs = st.tabs(["1. Household", "2. Income", "3. Spending", "4. Social Security", "5. Assets & Debt", "6. Spouse / Partner"])

    with tabs[0]:
        st.subheader("Household Basics")
        c1, c2, c3 = st.columns(3)
        c1.text_input("First name", key="name", help="Used only to personalize the dashboard greeting and report language.")
        c2.number_input("Current age", min_value=45, max_value=90, key="phase1_age", value=int(st.session_state.age), on_change=apply_household_updates, help="Your current age today. The app uses this to calculate how many years you have until retirement and how long the plan must last. This auto-saves during your session.")
        c3.slider("Retirement age", 50, 75, key="phase1_retire_age", value=int(st.session_state.retire_age), on_change=apply_household_updates, help="The age you want to test for retirement. You can compare multiple ages later in Phase 2. This auto-saves during your session.")
        c4, c5 = st.columns(2)
        c4.slider("Plan through age", 75, 100, key="plan_age", help="The age the projection should run through. Many retirement plans use age 90 or 95 to test longevity risk.")
        planning_depth = c5.selectbox("Planning depth", ["Simple", "Standard", "Advanced"], index=1, help="Choose how detailed the planning should be. Simple is quick, Standard adds major assumptions, and Advanced includes tax and strategy details.")
        if st.button("Apply household updates", on_click=apply_household_updates):
            st.success("Household updates applied.")
        if planning_depth == "Advanced":
            st.info("Advanced mode adds more assumptions in Phase 2 and Phase 3.")

    with tabs[1]:
        st.subheader("Income")
        c1, c2, c3 = st.columns(3)
        c1.number_input("Current household income", min_value=0, step=5000, key="current_income", help="Your current annual household earned income before taxes. This helps estimate savings ability and retirement transition risk.")
        c2.number_input("Annual pension income", min_value=0, step=1000, key="pension_income", help="Expected annual pension income in retirement, if any. Enter the yearly amount before taxes.")
        c3.number_input("Other annual income", min_value=0, step=1000, key="other_income", help="Other recurring yearly retirement income, such as rental income, annuity income, part-time work, or business income.")
        st.text_area("Other income notes", placeholder="Rental income, part-time work, annuity, business income...", help="Optional notes about where other income comes from and whether it is guaranteed, temporary, or uncertain.")

    with tabs[2]:
        st.subheader("Spending")
        st.number_input(
            "Estimated monthly retirement spending",
            min_value=0,
            step=500,
            key="phase1_monthly_spending",
            value=int(st.session_state.monthly_spending),
            on_change=apply_spending_updates,
            help="Your estimated average monthly spending in retirement. Include normal living costs, travel, insurance, healthcare, hobbies, and recurring bills. This auto-saves during your session.",
        )
        if st.button("Apply spending update"):
            st.session_state.monthly_spending = st.session_state.phase1_monthly_spending
            st.success(f"Monthly spending updated to {money(st.session_state.monthly_spending)}.")
        with st.expander("Detailed monthly budget"):
            cats = ["Housing", "Utilities", "Food", "Healthcare", "Travel", "Insurance", "Vehicles", "Entertainment", "Family support", "Other"]
            cols = st.columns(2)
            total = 0
            for i, cat in enumerate(cats):
                with cols[i % 2]:
                    total += st.number_input(cat, min_value=0, step=100, key=f"budget_{cat.lower().replace(' ', '_')}", help=f"Estimated monthly spending for {cat.lower()} in retirement.")
            if st.button("Use detailed budget total"):
                st.session_state.monthly_spending = total
                st.success(f"Monthly spending updated to {money(total)}.")

    with tabs[3]:
        st.subheader("Social Security")
        st.session_state.ss_fra_age = 67
        c1, c2 = st.columns(2)
        c1.number_input(
            "Your annual Social Security at full retirement age",
            min_value=0,
            step=1000,
            key="social_security",
            help="Enter your estimated annual benefit at full retirement age from SSA.gov. The app assumes full retirement age is 67 and adjusts the estimate up or down based on the claiming age you choose."
        )
        c2.slider(
            "Your Social Security start age",
            62,
            70,
            key="ss_start_age",
            help="Choose when you plan to claim. Filing before age 67 reduces benefits; delaying after age 67 increases benefits until age 70."
        )
        user_ss_factor = ss_claiming_factor(st.session_state.ss_start_age, 67)
        st.info(
            f"Estimated Social Security at claiming age {st.session_state.ss_start_age}: "
            f"{money(adjusted_user_social_security())} per year "
            f"({user_ss_factor * 100:.0f}% of the age-67 estimate)."
        )
        st.caption("This is a simplified estimate using age 67 as full retirement age. SSA calculates benefits by month and individual birth year, so users should confirm exact numbers at SSA.gov.")

    with tabs[4]:
        st.subheader("Assets & Debt")
        c1, c2, c3 = st.columns(3)
        c1.number_input("Traditional 401k / IRA", min_value=0, step=10000, key="traditional", help="Current balance in pre-tax retirement accounts such as traditional 401(k), traditional IRA, 403(b), or similar accounts.")
        c2.number_input("Roth balance", min_value=0, step=10000, key="roth", help="Current Roth retirement balance. Roth money may provide tax-free withdrawals if rules are met.")
        c3.number_input("Taxable / cash", min_value=0, step=10000, key="taxable_cash", help="Taxable brokerage, savings, money market, CDs, checking, or other non-retirement cash/investments.")
        c4, c5 = st.columns(2)
        c4.number_input("Home value", min_value=0, step=10000, key="home_value", help="Estimated current market value of your home. This helps estimate home equity and downsizing flexibility.")
        c5.number_input("Mortgage balance", min_value=0, step=10000, key="mortgage", help="Remaining mortgage balance or other debt secured by the home.")
        st.session_state.home_equity = max(0, st.session_state.home_value - st.session_state.mortgage)

    with tabs[5]:
        st.subheader("Spouse / Partner")
        st.checkbox("Include spouse or partner", key="spouse_enabled", help="Turn this on if your retirement plan should include a spouse or partner’s age, income, and Social Security.")
        if st.session_state.spouse_enabled:
            c1, c2, c3 = st.columns(3)
            c1.number_input("Spouse age", min_value=45, max_value=90, key="spouse_age", help="Your spouse or partner’s current age. This affects retirement timing, Social Security timing, and survivor planning.")
            c2.number_input("Spouse annual income", min_value=0, step=5000, key="spouse_income", help="Your spouse or partner’s current annual earned income before taxes.")
            c3.number_input("Spouse annual Social Security at full retirement age", min_value=0, step=1000, key="spouse_ss", help="Estimated annual Social Security benefit for your spouse or partner at full retirement age. The app adjusts this based on claiming age.")
            st.session_state.spouse_ss_fra_age = 67
            st.slider("Spouse Social Security start age", 62, 70, key="spouse_ss_start_age", help="The age your spouse or partner expects to claim Social Security. The app assumes full retirement age is 67.")
            spouse_factor = ss_claiming_factor(st.session_state.spouse_ss_start_age, 67)
            st.info(
                f"Estimated spouse Social Security at claiming age {st.session_state.spouse_ss_start_age}: "
                f"{money(adjusted_spouse_social_security())} per year "
                f"({spouse_factor * 100:.0f}% of the age-67 estimate)."
            )
        else:
            st.info("No spouse or partner is included in this plan.")

    st.divider()
    st.subheader("Foundation Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual Spending", money(annual_spending()))
    c2.metric("Guaranteed Income", money(guaranteed_income()))
    c3.metric("Portfolio", money(portfolio_total()))
    c4.metric("Home Equity", money(st.session_state.home_equity))
    st.success("Inputs are automatically saved during this browser session. Use Phase 5 to save/export a named plan you want to keep after refresh or redeploy.")


def phase2_table(compare_ages, return_scenario):
    return_map = {"Conservative": 5.0, "Base": st.session_state.growth_return, "Bad first years": 3.5}
    r = return_map[return_scenario]
    rows = []
    for age in compare_ages:
        df = project_portfolio(retire_age=age, return_rate=r)
        retire_port = df.loc[df["Age"] == age, "Portfolio"].iloc[0] if age in df["Age"].values else df["Portfolio"].iloc[0]
        end_port = df["Portfolio"].iloc[-1]
        first_withdrawal = max(0, annual_spending() - guaranteed_income())
        bridge_years = max(0, 65 - age)
        healthcare_bridge = bridge_years * float(st.session_state.healthcare_monthly) * 12
        score = int(max(0, min(100, 55 + (end_port / max(portfolio_total(), 1)) * 20 - bridge_years * 3)))
        rows.append({
            "Retire Age": age,
            "Readiness Score": score,
            "Portfolio at Retirement": retire_port,
            "Ending Portfolio": end_port,
            "First-Year Portfolio Need": first_withdrawal,
            "Healthcare Bridge": healthcare_bridge,
        })
    return pd.DataFrame(rows)


def show_phase2():
    st.title("Phase 2 — Retirement Lab")
    st.write("Compare retirement ages, adjust average returns, and see how much the portfolio could grow or shrink over time.")
    section_guide(
        "Phase 2 — Retirement Lab",
        "Use this phase to experiment. Compare different retirement ages, adjust expected return rates from 0% to 25%, and test your two-bucket strategy with separate safe and growth returns.",
        "It shows how retirement timing and investment assumptions affect projected portfolio value, withdrawal pressure, healthcare bridge years, and overall retirement confidence.",
        "Do not treat high return settings as guaranteed. Use conservative, base, and optimistic assumptions to understand your range of outcomes."
    )
    st.markdown("<div class='soft-box'>This lab uses your Phase 1 inputs. Adjust the return rate, retirement age, and planning age to see a projection table, chart, and plain-English takeaway.</div>", unsafe_allow_html=True)

    default_ages = sorted(set([int(st.session_state.retire_age), 62, 65, 67]))

    c1, c2, c3 = st.columns([2, 1, 1])
    compare_ages = c1.multiselect(
        "Retirement ages to compare",
        list(range(50, 76)),
        default=default_ages,
        key="phase2_compare_ages_widget",
        help="Choose the retirement ages you want to compare side-by-side, such as 58, 62, 65, and 67.",
    )
    selected_return = c2.slider(
        "Average annual return (%)",
        min_value=0.0,
        max_value=25.0,
        value=min(25.0, max(0.0, float(st.session_state.growth_return))),
        step=0.25,
        key="phase2_avg_return",
        help="Use this to test conservative, base, optimistic, or very aggressive long-term return assumptions.",
    )
    projection_view = c3.selectbox(
        "Projection view",
        ["Selected return", "Compare 4% / 6% / 8%", "Bear / Base / Bull"],
        key="phase2_projection_view",
        help="Choose whether to view only your selected return or compare multiple return scenarios.",
    )

    st.divider()
    st.subheader("Two-Bucket Strategy")
    st.write("Model a safer near-term bucket and a growth bucket with different return assumptions.")
    section_guide(
        "Two-Bucket Strategy",
        "Put near-term spending money in Bucket 1 and long-term growth money in Bucket 2. Then assign each bucket its own return rate.",
        "This estimates a blended portfolio return and helps show whether you have enough safer money to cover early retirement spending without selling growth assets during a downturn.",
        "A common starting point is 2–3 years of spending in Bucket 1, but the right amount depends on risk comfort, income sources, and market conditions."
    )

    b1, b2, b3 = st.columns(3)
    b1.number_input(
        "Bucket 1 balance",
        min_value=0,
        step=10000,
        key="bucket1_balance",
        help="Money intended for near-term retirement spending. This is usually cash, CDs, short-term bonds, or other lower-volatility assets.",
    )
    b2.number_input(
        "Bucket 2 balance",
        min_value=0,
        step=10000,
        key="bucket2_balance",
        help="Money intended for long-term growth. This is usually a more aggressive investment bucket held for later retirement years.",
    )
    b3.number_input(
        "Bucket 1 spending years",
        min_value=1,
        max_value=7,
        step=1,
        key="bucket1_years",
        help="How many years of spending you want in the safer bucket. A common planning range is about 2–4 years.",
    )

    r1, r2, r3 = st.columns(3)
    r1.slider(
        "Bucket 1 return (%)",
        min_value=0.0,
        max_value=25.0,
        value=float(st.session_state.bucket1_return),
        step=0.25,
        key="bucket1_return",
        help="Expected annual return for the safer bucket. Lower-risk assets often use a lower return assumption.",
    )
    r2.slider(
        "Bucket 2 return (%)",
        min_value=0.0,
        max_value=25.0,
        value=float(st.session_state.bucket2_return),
        step=0.25,
        key="bucket2_return",
        help="Expected annual return for the growth bucket. This is usually higher, but also assumes more volatility.",
    )
    r3.button(
        "Auto-split from portfolio",
        use_container_width=True,
        help="Sets Bucket 1 to your annual spending times your target Bucket 1 years, then puts the rest in Bucket 2.",
        on_click=auto_bucket_split,
    )

    blended = bucket_blended_return()
    total_bucket = bucket_total()
    total_gap = portfolio_total() - total_bucket
    m1, m2, m3 = st.columns(3)
    m1.metric("Bucket Total", money(total_bucket))
    m2.metric("Weighted Avg Return", f"{blended:.2f}%")
    m3.metric("Portfolio Difference", money(total_gap))
    if abs(total_gap) > 1000:
        st.warning("Your Bucket 1 + Bucket 2 total does not match your total portfolio from Phase 1. Use Auto-split or adjust the bucket balances if you want them to match.")

    if not compare_ages:
        st.warning("Choose at least one retirement age to compare.")
        return

    # Scenario table by retirement age using the selected return rate
    result = phase2_table(compare_ages, "Base")
    manual_rows = []
    for age in compare_ages:
        df_age = project_portfolio(retire_age=age, return_rate=selected_return)
        retire_port = df_age.loc[df_age["Age"] == age, "Portfolio"].iloc[0] if age in df_age["Age"].values else df_age["Portfolio"].iloc[0]
        end_port = df_age["Portfolio"].iloc[-1]
        first_withdrawal = max(0, annual_spending() - guaranteed_income())
        bridge_years = max(0, 65 - int(age))
        healthcare_bridge = bridge_years * float(st.session_state.healthcare_monthly) * 12
        score = int(max(0, min(100, 55 + (end_port / max(portfolio_total(), 1)) * 20 - bridge_years * 3)))
        manual_rows.append({
            "Retire Age": int(age),
            "Readiness Score": score,
            "Portfolio at Retirement": retire_port,
            "Ending Portfolio": end_port,
            "First-Year Portfolio Need": first_withdrawal,
            "Healthcare Bridge": healthcare_bridge,
        })
    result = pd.DataFrame(manual_rows)

    st.subheader("Retirement Age Comparison")
    display = result.copy()
    for col in ["Portfolio at Retirement", "Ending Portfolio", "First-Year Portfolio Need", "Healthcare Bridge"]:
        display[col] = display[col].apply(money)
    st.dataframe(display, use_container_width=True, hide_index=True)

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=result["Retire Age"], y=result["Ending Portfolio"], name="Ending Portfolio"))
    fig_bar.update_layout(
        height=340,
        title=f"Ending Portfolio by Retirement Age at {selected_return:.2f}% Return",
        yaxis_tickprefix="$",
        xaxis_title="Retirement Age",
        margin=dict(l=10, r=10, t=55, b=10),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()
    st.subheader("Return Rate Projection")
    st.write("This shows how much the portfolio may be worth each year based on the return assumption and retirement withdrawal need.")

    if projection_view == "Selected return":
        return_scenarios = {f"Selected Return {selected_return:.2f}%": selected_return}
    elif projection_view == "Compare 4% / 6% / 8%":
        return_scenarios = {"Conservative 4%": 4.0, "Moderate 6%": 6.0, "Growth 8%": 8.0}
    else:
        return_scenarios = {"Bear 3%": 3.0, f"Base {selected_return:.2f}%": selected_return, "Bull 9%": 9.0}

    projection_rows = []
    fig_line = go.Figure()
    for label, rate in return_scenarios.items():
        df_proj = project_portfolio(retire_age=st.session_state.retire_age, return_rate=rate)
        fig_line.add_trace(go.Scatter(x=df_proj["Age"], y=df_proj["Portfolio"], mode="lines", name=label, line=dict(width=3)))
        for _, row in df_proj.iterrows():
            projection_rows.append({
                "Scenario": label,
                "Age": int(row["Age"]),
                "Portfolio": row["Portfolio"],
                "Annual Withdrawal": row["Withdrawal"],
            })

    fig_line.add_vline(x=st.session_state.retire_age, line_dash="dash", annotation_text="Retire")
    fig_line.add_vline(x=st.session_state.ss_start_age, line_dash="dot", annotation_text="Social Security")
    fig_line.update_layout(
        height=420,
        title="Portfolio Projection by Return Assumption",
        yaxis_tickprefix="$",
        xaxis_title="Age",
        yaxis_title="Portfolio",
        margin=dict(l=10, r=10, t=55, b=10),
    )
    st.plotly_chart(fig_line, use_container_width=True)

    projection_df = pd.DataFrame(projection_rows)
    table_df = projection_df.copy()
    table_df["Portfolio"] = table_df["Portfolio"].apply(money)
    table_df["Annual Withdrawal"] = table_df["Annual Withdrawal"].apply(money)
    st.subheader("Projection Table")
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    csv = projection_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download projection CSV",
        data=csv,
        file_name="retirement_return_projection.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()
    st.subheader("Two-Bucket Projection")
    st.write("This view shows how Bucket 1 and Bucket 2 may move over time using their separate return assumptions.")
    bucket_df = project_two_bucket(retire_age=st.session_state.retire_age)
    fig_bucket = go.Figure()
    fig_bucket.add_trace(go.Scatter(x=bucket_df["Age"], y=bucket_df["Bucket 1"], mode="lines", name="Bucket 1 — safer money", line=dict(width=3)))
    fig_bucket.add_trace(go.Scatter(x=bucket_df["Age"], y=bucket_df["Bucket 2"], mode="lines", name="Bucket 2 — growth money", line=dict(width=3)))
    fig_bucket.add_trace(go.Scatter(x=bucket_df["Age"], y=bucket_df["Total Portfolio"], mode="lines", name="Total", line=dict(width=4, dash="dash")))
    fig_bucket.add_vline(x=st.session_state.retire_age, line_dash="dash", annotation_text="Retire")
    fig_bucket.update_layout(
        height=430,
        title="Two-Bucket Portfolio Projection",
        yaxis_tickprefix="$",
        xaxis_title="Age",
        yaxis_title="Balance",
        margin=dict(l=10, r=10, t=55, b=10),
    )
    st.plotly_chart(fig_bucket, use_container_width=True)

    bucket_table = bucket_df.copy()
    for col in ["Bucket 1", "Bucket 2", "Total Portfolio", "Annual Withdrawal", "Transfer to Bucket 1"]:
        bucket_table[col] = bucket_table[col].apply(money)
    st.dataframe(bucket_table, use_container_width=True, hide_index=True)
    st.download_button(
        "Download two-bucket projection CSV",
        data=bucket_df.to_csv(index=False).encode("utf-8"),
        file_name="two_bucket_projection.csv",
        mime="text/csv",
        use_container_width=True,
    )

    best = result.sort_values("Readiness Score", ascending=False).iloc[0]
    selected_df = project_portfolio(retire_age=st.session_state.retire_age, return_rate=selected_return)
    ending_balance = selected_df["Portfolio"].iloc[-1]
    retirement_balance = selected_df.loc[selected_df["Age"] == st.session_state.retire_age, "Portfolio"].iloc[0] if st.session_state.retire_age in selected_df["Age"].values else selected_df["Portfolio"].iloc[0]
    total_growth = max(0, retirement_balance - portfolio_total())

    st.markdown(
        f"<div class='success-box'><b>Plain-English takeaway:</b> At a <b>{selected_return:.2f}%</b> average return, your portfolio could grow by about <b>{money(total_growth)}</b> before retirement at age <b>{int(st.session_state.retire_age)}</b>. In this comparison, retiring at <b>{int(best['Retire Age'])}</b> has the strongest score. The biggest pressure points are the healthcare bridge before Medicare, the annual portfolio withdrawal need, and whether Bucket 1 is large enough to avoid selling growth assets during bad markets.</div>",
        unsafe_allow_html=True,
    )



# ------------------------------------------------------------
# Simplified federal tax estimator helpers
# ------------------------------------------------------------
STANDARD_DEDUCTIONS_2026 = {
    "Single": 16100,
    "Married Filing Jointly": 32200,
    "Head of Household": 24150,
}

FEDERAL_BRACKETS_2026 = {
    "Single": [
        (0, 12400, 0.10),
        (12400, 50400, 0.12),
        (50400, 105700, 0.22),
        (105700, 201775, 0.24),
        (201775, 256225, 0.32),
        (256225, 640600, 0.35),
        (640600, float("inf"), 0.37),
    ],
    "Married Filing Jointly": [
        (0, 24800, 0.10),
        (24800, 100800, 0.12),
        (100800, 211400, 0.22),
        (211400, 403550, 0.24),
        (403550, 512450, 0.32),
        (512450, 768700, 0.35),
        (768700, float("inf"), 0.37),
    ],
    "Head of Household": [
        (0, 17700, 0.10),
        (17700, 67450, 0.12),
        (67450, 105700, 0.22),
        (105700, 201775, 0.24),
        (201775, 256200, 0.32),
        (256200, 640600, 0.35),
        (640600, float("inf"), 0.37),
    ],
}


def calc_progressive_tax(taxable_income, brackets):
    taxable_income = max(0, float(taxable_income))
    total = 0.0
    marginal_rate = 0.0
    bracket_rows = []
    for lower, upper, rate in brackets:
        if taxable_income <= lower:
            break
        taxed_amount = min(taxable_income, upper) - lower
        taxed_amount = max(0, taxed_amount)
        tax = taxed_amount * rate
        total += tax
        if taxed_amount > 0:
            marginal_rate = rate
        bracket_rows.append({
            "Bracket": f"{int(rate*100)}%",
            "Taxable dollars in bracket": taxed_amount,
            "Estimated tax from bracket": tax,
        })
    effective_rate = total / taxable_income if taxable_income > 0 else 0
    return total, marginal_rate, effective_rate, bracket_rows


def estimate_taxable_income_components(gross_income, withdrawal_need):
    ss_taxable = adjusted_user_social_security() * (st.session_state.taxable_ss_percent / 100)
    if st.session_state.spouse_enabled:
        ss_taxable += adjusted_spouse_social_security() * (st.session_state.taxable_ss_percent / 100)
    ordinary_income = (
        ss_taxable
        + st.session_state.pension_income
        + st.session_state.other_income
        + st.session_state.other_taxable_income
        + withdrawal_need
        + st.session_state.roth_conversion
    )
    filing_status = st.session_state.filing_status
    standard = STANDARD_DEDUCTIONS_2026.get(filing_status, 16100)
    deduction = max(float(st.session_state.itemized_deductions), standard) if st.session_state.use_itemized else standard
    taxable_income = max(0, ordinary_income - deduction)
    return {
        "taxable_social_security": ss_taxable,
        "ordinary_income_before_deduction": ordinary_income,
        "deduction": deduction,
        "taxable_income": taxable_income,
    }


def format_tax_brackets_for_display(filing_status):
    rows = []
    for lower, upper, rate in FEDERAL_BRACKETS_2026.get(filing_status, FEDERAL_BRACKETS_2026["Single"]):
        high = "and up" if upper == float("inf") else money(upper)
        rows.append({"Rate": f"{int(rate*100)}%", "Taxable income range": f"{money(lower)} to {high}"})
    return pd.DataFrame(rows)


def withdrawal_strategy_rules(age, retire_age, ss_start_age, traditional, roth, taxable_cash, hsa_balance, bucket1_balance, spending, guaranteed, tax_rate, aca_target, roth_conversion, rule55_eligible, aca_sensitive, rmd_concern, market_downturn):
    """Simple educational rule engine for tax-smart withdrawal order."""
    withdrawal_need = max(0, spending - guaranteed)
    taxable_income_est = guaranteed + withdrawal_need + roth_conversion
    pre_595 = age < 59.5
    pre_medicare = age < 65
    pre_ss = age < ss_start_age
    rmd_pressure = traditional > 600000 or rmd_concern in ["High", "Very High"]

    order = []
    reasons = []
    warnings = []
    opportunities = []

    if market_downturn and bucket1_balance > 0:
        order.append(("1", "Bucket 1 / cash reserve", "Use safer assets first during downturns to avoid selling growth investments when they may be temporarily down."))
        warnings.append("Market downturn mode is on. Preserving Bucket 2 growth assets may reduce sequence-of-return damage.")
    elif bucket1_balance > 0:
        order.append(("1", "Bucket 1 / cash reserve", "Use near-term cash/safe assets for planned spending and market-crash protection."))

    if pre_595:
        if rule55_eligible and traditional > 0:
            order.append(("2", "Current employer 401(k) / Rule of 55, if eligible", "If you separate from service in or after the year you turn 55, some 401(k) withdrawals may avoid the 10% early-withdrawal penalty."))
            reasons.append("Because you are under 59½, early-withdrawal penalty rules matter.")
        if taxable_cash > 0:
            order.append(("3", "Taxable savings / brokerage", "Taxable assets can provide flexibility before 59½ and can help manage income before Medicare."))
    else:
        if taxable_cash > 0:
            order.append(("2", "Taxable savings / brokerage", "Use taxable assets strategically for flexibility while managing capital gains and tax brackets."))
        if traditional > 0:
            order.append(("3", "Traditional IRA / 401(k)", "Withdraw enough to fill attractive tax brackets, especially before RMDs begin."))

    if pre_medicare and aca_sensitive:
        warnings.append("You are before Medicare age. Large traditional withdrawals or Roth conversions may raise MAGI and affect ACA subsidy eligibility.")
        if taxable_income_est > aca_target and aca_target > 0:
            warnings.append(f"Modeled taxable income of {money(taxable_income_est)} is above your ACA target of {money(aca_target)}.")
        else:
            opportunities.append("Income appears near/below the ACA target, which may preserve healthcare subsidy flexibility.")

    if roth_conversion > 0:
        opportunities.append(f"Testing {money(roth_conversion)} in Roth conversions may reduce future RMD pressure, but it raises current taxable income.")
    elif (pre_ss or pre_medicare) and traditional > 0 and tax_rate <= 22:
        opportunities.append("Low-income gap years before Social Security/Medicare can be a useful window to test Roth conversions.")

    if rmd_pressure:
        opportunities.append("Traditional account balance is large enough to create possible RMD pressure later. Consider bracket-filling Roth conversions or controlled withdrawals before RMD age.")

    if roth > 0:
        order.append(("Later", "Roth IRA / Roth 401(k)", "Usually preserve Roth money as long as possible because qualified withdrawals are tax-free and flexible."))
    if hsa_balance > 0:
        order.append(("Last / medical", "HSA", "If eligible, preserve HSA dollars for qualified healthcare expenses because they can be triple-tax advantaged."))

    # Deduplicate by account label while preserving order.
    seen = set()
    unique = []
    for row in order:
        if row[1] not in seen:
            unique.append(row)
            seen.add(row[1])

    if not warnings:
        warnings.append("No major red flags based on the simplified inputs, but tax rules should be reviewed before acting.")
    if not opportunities:
        opportunities.append("The biggest opportunity is to coordinate spending, tax brackets, healthcare income limits, and RMD timing.")

    return unique, warnings, opportunities, withdrawal_need, taxable_income_est


def show_phase3():
    st.title("Phase 3 — Income & Tax")
    st.write("Estimate retirement income sources, portfolio withdrawal need, tax pressure, Roth conversion impact, future RMD risk, and a tax-smart account drawdown order.")
    section_guide(
        "Phase 3 — Income & Tax",
        "Enter tax assumptions, Roth conversion ideas, account balances, and healthcare/tax sensitivity. Then review the income mix, estimated tax pressure, RMD preview, and withdrawal order recommendations.",
        "This phase helps identify which income sources may cover spending, how much may need to come from investments, and which account types may be most tax-efficient to draw from first.",
        "This is educational planning, not tax advice. The goal is to surface questions and scenarios to review with a tax professional or financial advisor."
    )
    st.markdown("<div class='soft-box'>This is a planning estimate, not tax advice. The goal is to show pressure points and help users know what to ask a financial or tax professional.</div>", unsafe_allow_html=True)

    st.subheader("Filing status & tax setup")
    t1, t2, t3, t4 = st.columns(4)
    t1.selectbox("Filing status", ["Single", "Married Filing Jointly", "Head of Household"], key="filing_status", help="Choose the tax filing status to estimate the federal brackets and standard deduction. Married Filing Jointly usually applies to spouses filing one combined return.")
    t2.selectbox("Tax year", ["2026"], key="tax_year", help="The tax estimator currently uses simplified 2026 federal brackets and standard deductions.")
    t3.number_input("State tax rate (%)", min_value=0.0, max_value=15.0, step=0.25, key="state_tax_rate", help="Estimated state income tax rate. Some states have no income tax; others tax retirement income differently. Use this as a planning placeholder.")
    t4.number_input("Taxable Social Security (%)", min_value=0.0, max_value=85.0, step=5.0, key="taxable_ss_percent", help="Federal rules can make up to 85% of Social Security taxable depending on provisional income. Use 85% for conservative planning, lower if income is modest.")

    t5, t6, t7 = st.columns(3)
    t5.number_input("Other taxable income", min_value=0, step=1000, key="other_taxable_income", help="Interest, dividends, taxable side income, rental income, or other ordinary taxable income not already entered elsewhere.")
    t6.checkbox("Use itemized deductions", key="use_itemized", help="Check this if itemized deductions may exceed the standard deduction.")
    if st.session_state.use_itemized:
        t7.number_input("Itemized deductions", min_value=0, step=1000, key="itemized_deductions", help="Estimated deductible mortgage interest, charitable giving, eligible taxes, medical deductions, and other itemized deductions.")
    else:
        t7.metric("Standard deduction", money(STANDARD_DEDUCTIONS_2026.get(st.session_state.filing_status, 16100)))

    st.subheader("Income & tax assumptions")
    c1, c2, c3 = st.columns(3)
    c1.number_input("Estimated effective tax rate (%)", min_value=0.0, max_value=40.0, step=0.5, key="tax_rate", help="Estimated average tax rate on retirement income. This is not a tax filing calculation, just a planning assumption.")
    c2.number_input("Annual Roth conversion to test", min_value=0, step=5000, key="roth_conversion", help="Amount of traditional IRA/401(k) money to model converting into Roth each year. This may raise taxes now but reduce future RMD pressure.")
    c3.number_input("ACA target MAGI", min_value=0, step=5000, key="aca_target_income", help="Target Modified Adjusted Gross Income before Medicare age if you want to model ACA health insurance subsidy flexibility.")

    gross_income = guaranteed_income()
    spending = annual_spending()
    withdrawal_need = max(0, spending - gross_income)
    tax_components = estimate_taxable_income_components(gross_income, withdrawal_need)
    federal_tax, marginal_rate, effective_rate, bracket_rows = calc_progressive_tax(
        tax_components["taxable_income"],
        FEDERAL_BRACKETS_2026.get(st.session_state.filing_status, FEDERAL_BRACKETS_2026["Single"]),
    )
    state_tax = tax_components["taxable_income"] * st.session_state.state_tax_rate / 100
    estimated_tax = federal_tax + state_tax
    after_tax_gap = max(0, spending + estimated_tax - gross_income)
    rmd_age = 75
    years_to_rmd = max(0, rmd_age - st.session_state.age)
    future_traditional = st.session_state.traditional * ((1 + st.session_state.growth_return / 100) ** years_to_rmd)
    estimated_rmd = future_traditional / 24.6 if years_to_rmd >= 0 else 0

    a, b, c, d = st.columns(4)
    a.metric("Guaranteed Income", money(gross_income))
    b.metric("Portfolio Withdrawal Need", money(withdrawal_need))
    c.metric("Estimated Tax", money(estimated_tax))
    d.metric("Estimated First RMD", money(estimated_rmd))

    st.markdown("### Federal tax estimate by filing status")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Taxable Income", money(tax_components["taxable_income"]))
    k2.metric("Federal Tax", money(federal_tax))
    k3.metric("Marginal Rate", f"{marginal_rate*100:.0f}%")
    k4.metric("Effective Federal Rate", f"{effective_rate*100:.1f}%")

    with st.expander("Show taxable income breakdown and bracket table", expanded=False):
        breakdown_df = pd.DataFrame([
            {"Component": "Taxable Social Security estimate", "Amount": tax_components["taxable_social_security"]},
            {"Component": "Pension income", "Amount": st.session_state.pension_income},
            {"Component": "Other income", "Amount": st.session_state.other_income},
            {"Component": "Other taxable income", "Amount": st.session_state.other_taxable_income},
            {"Component": "Portfolio withdrawal need", "Amount": withdrawal_need},
            {"Component": "Roth conversion tested", "Amount": st.session_state.roth_conversion},
            {"Component": "Deduction used", "Amount": -tax_components["deduction"]},
            {"Component": "Estimated taxable income", "Amount": tax_components["taxable_income"]},
        ])
        st.dataframe(breakdown_df, use_container_width=True, hide_index=True, column_config={"Amount": st.column_config.NumberColumn(format="$%d")})

        bracket_col, tax_col = st.columns(2)
        with bracket_col:
            st.markdown(f"**2026 federal brackets — {st.session_state.filing_status}**")
            st.dataframe(format_tax_brackets_for_display(st.session_state.filing_status), use_container_width=True, hide_index=True)
        with tax_col:
            st.markdown("**Estimated tax by bracket**")
            bracket_tax_df = pd.DataFrame(bracket_rows)
            if not bracket_tax_df.empty:
                st.dataframe(bracket_tax_df, use_container_width=True, hide_index=True, column_config={"Taxable dollars in bracket": st.column_config.NumberColumn(format="$%d"), "Estimated tax from bracket": st.column_config.NumberColumn(format="$%d")})
            else:
                st.info("No federal tax estimated after deductions.")

    st.info("Tax notes: this is a simplified federal ordinary-income estimate. It does not fully calculate capital gains, qualified dividends, Medicare IRMAA, AMT, credits, deductions phaseouts, state-specific exclusions, or exact Social Security taxation formulas.")

    income_df = pd.DataFrame({
        "Source": ["Social Security", "Pension", "Other Income", "Portfolio Withdrawal"],
        "Amount": [adjusted_user_social_security() + adjusted_spouse_social_security(), st.session_state.pension_income, st.session_state.other_income, withdrawal_need],
    })
    fig = go.Figure(data=[go.Pie(labels=income_df["Source"], values=income_df["Amount"], hole=0.55)])
    fig.update_layout(height=340, title="Retirement Income Mix")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Tax-Smart Withdrawal Order Optimizer")
    st.write("This module recommends which account types to consider drawing from first based on age, taxes, healthcare sensitivity, RMD pressure, and your bucket strategy.")
    section_guide(
        "Withdrawal Order Optimizer",
        "Enter balances for cash/taxable accounts, traditional IRA/401(k), Roth accounts, and HSA. Then check whether Rule of 55, ACA sensitivity, RMD concerns, or market downturn mode apply.",
        "It produces a suggested account drawdown order, watch-outs, and tax-saving opportunities based on your situation.",
        "The recommendation changes depending on age, pre-Medicare healthcare needs, RMD pressure, and whether you want to preserve Roth assets for later."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.number_input("Taxable / cash balance", min_value=0, step=10000, key="taxable_cash", help="Money in savings, money market, CDs, taxable brokerage, or other non-retirement accounts available for flexible withdrawals.")
    c2.number_input("Traditional IRA / 401(k)", min_value=0, step=10000, key="traditional", help="Pre-tax retirement accounts. Withdrawals are generally taxable and may create RMDs later.")
    c3.number_input("Roth IRA / Roth 401(k)", min_value=0, step=10000, key="roth", help="After-tax retirement accounts. Qualified withdrawals are generally tax-free and can provide tax flexibility.")
    c4.number_input("HSA balance", min_value=0, step=1000, key="hsa_balance", help="Health Savings Account balance. Often best preserved for qualified medical expenses because of tax advantages.")

    c5, c6, c7, c8 = st.columns(4)
    c5.checkbox("Rule of 55 may apply", key="rule55_eligible", help="Check this if you may leave your employer in or after the year you turn 55 and want the app to consider 401(k) access before 59½.")
    c6.checkbox("ACA subsidy sensitive", key="aca_sensitive", help="Check this if you may retire before Medicare and want to control taxable income for healthcare subsidy planning.")
    c7.selectbox("RMD concern level", ["Low", "Medium", "High", "Very High"], key="rmd_concern", help="How concerned you are about large taxable Required Minimum Distributions later in retirement.")
    c8.checkbox("Market downturn mode", key="market_downturn", help="Check this to prioritize using Bucket 1/cash before selling growth assets during a bad market.")

    order, warnings, opportunities, need, taxable_income_est = withdrawal_strategy_rules(
        age=st.session_state.age,
        retire_age=st.session_state.retire_age,
        ss_start_age=st.session_state.ss_start_age,
        traditional=st.session_state.traditional,
        roth=st.session_state.roth,
        taxable_cash=st.session_state.taxable_cash,
        hsa_balance=st.session_state.hsa_balance,
        bucket1_balance=st.session_state.bucket1_balance,
        spending=spending,
        guaranteed=gross_income,
        tax_rate=st.session_state.tax_rate,
        aca_target=st.session_state.aca_target_income,
        roth_conversion=st.session_state.roth_conversion,
        rule55_eligible=st.session_state.rule55_eligible,
        aca_sensitive=st.session_state.aca_sensitive,
        rmd_concern=st.session_state.rmd_concern,
        market_downturn=st.session_state.market_downturn,
    )

    st.markdown("### Recommended drawdown order")
    order_df = pd.DataFrame(order, columns=["Priority", "Account / Strategy", "Why it may fit"])
    st.dataframe(order_df, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Modeled Withdrawal Need", money(need))
    c2.metric("Modeled Taxable Income", money(taxable_income_est))
    c3.metric("Traditional Balance", money(st.session_state.traditional))

    left, right = st.columns(2)
    with left:
        st.markdown("### Watch-outs")
        for item in warnings:
            st.warning(item)
    with right:
        st.markdown("### Tax-saving opportunities")
        for item in opportunities:
            st.success(item)

    if st.session_state.roth_conversion > 0:
        st.info(f"Testing a {money(st.session_state.roth_conversion)} annual Roth conversion increases near-term taxable income, but may reduce future RMD pressure if repeated strategically.")
    if gross_income + withdrawal_need > st.session_state.aca_target_income:
        st.warning("Your modeled income may be above the ACA target. This could reduce healthcare subsidy eligibility before Medicare.")
    else:
        st.success("Your modeled income is near or below the ACA target. That may help preserve healthcare subsidy flexibility before Medicare.")

    st.markdown(f"<div class='success-box'><b>Plain-English takeaway:</b> Your current spending creates an estimated portfolio withdrawal need of <b>{money(withdrawal_need)}</b> per year. A tax-smart order can help coordinate Bucket 1 cash, taxable assets, traditional withdrawals, Roth conversions, and Roth/HSA preservation. The key planning question is whether to use low-income years to reduce future taxable balances without disrupting healthcare subsidies or pushing income into higher brackets.</div>", unsafe_allow_html=True)


# -------------------- Phase 4 Lifestyle Data --------------------
STATE_DATA = [
    {"State":"Florida", "Tax":86, "Cost":62, "Healthcare":82, "Lifestyle":92, "Climate":88, "Golf":90, "Watch-outs":"Insurance, hurricanes, crowded coastal markets", "Places":"Sarasota; The Villages; St. Augustine; Naples"},
    {"State":"South Carolina", "Tax":88, "Cost":77, "Healthcare":76, "Lifestyle":90, "Climate":82, "Golf":88, "Watch-outs":"Humidity, hurricane risk near coast, healthcare varies by city", "Places":"Hilton Head; Greenville; Charleston suburbs; Aiken"},
    {"State":"Tennessee", "Tax":90, "Cost":82, "Healthcare":78, "Lifestyle":80, "Climate":74, "Golf":76, "Watch-outs":"Sales tax, hot summers, limited coastal lifestyle", "Places":"Knoxville; Chattanooga; Franklin; Tellico Village"},
    {"State":"North Carolina", "Tax":74, "Cost":72, "Healthcare":80, "Lifestyle":86, "Climate":78, "Golf":92, "Watch-outs":"State income tax, coastal hurricane exposure", "Places":"Pinehurst; Wilmington; Asheville; Raleigh suburbs"},
    {"State":"Arizona", "Tax":76, "Cost":68, "Healthcare":84, "Lifestyle":88, "Climate":76, "Golf":96, "Watch-outs":"Extreme summer heat, water risk, rising housing costs", "Places":"Scottsdale; Tucson; Mesa; Green Valley"},
    {"State":"Texas", "Tax":82, "Cost":70, "Healthcare":78, "Lifestyle":82, "Climate":70, "Golf":82, "Watch-outs":"Property taxes, heat, large driving distances", "Places":"Georgetown; Frisco; San Antonio; McAllen"},
    {"State":"Michigan", "Tax":70, "Cost":73, "Healthcare":84, "Lifestyle":74, "Climate":54, "Golf":72, "Watch-outs":"Winter climate, snowbird travel cost, property tax varies", "Places":"Traverse City; Grand Rapids; Ann Arbor; Plymouth/Canton"},
    {"State":"Nevada", "Tax":90, "Cost":66, "Healthcare":76, "Lifestyle":82, "Climate":76, "Golf":84, "Watch-outs":"Healthcare access outside metros, summer heat", "Places":"Henderson; Reno; Mesquite; Summerlin"},
    {"State":"Georgia", "Tax":75, "Cost":76, "Healthcare":78, "Lifestyle":82, "Climate":78, "Golf":80, "Watch-outs":"Traffic near Atlanta, humidity, property tax varies", "Places":"Savannah; Peachtree City; Augusta; Blue Ridge"},
    {"State":"California", "Tax":48, "Cost":38, "Healthcare":90, "Lifestyle":94, "Climate":94, "Golf":88, "Watch-outs":"High taxes, high housing cost, wildfire risk", "Places":"San Diego; Palm Springs; Santa Barbara; Monterey"},
]

PLACE_DATA = [
    {"Place":"Sarasota", "State":"Florida", "Type":"Coastal / Arts / Beach", "Affordability":62, "Healthcare":86, "Lifestyle":95, "Climate":88, "Golf":90, "Why":"Beach lifestyle, arts, restaurants, golf, strong retiree infrastructure.", "Watch-outs":"Housing and insurance can be expensive; hurricane exposure."},
    {"Place":"Hilton Head", "State":"South Carolina", "Type":"Coastal / Golf", "Affordability":58, "Healthcare":76, "Lifestyle":96, "Climate":84, "Golf":97, "Why":"Premier golf, beaches, bike paths, upscale retirement feel.", "Watch-outs":"Expensive housing and coastal storm exposure."},
    {"Place":"The Villages", "State":"Florida", "Type":"Active Adult / Golf Cart", "Affordability":72, "Healthcare":78, "Lifestyle":92, "Climate":88, "Golf":96, "Why":"Highly social active-adult lifestyle with golf-cart convenience.", "Watch-outs":"Not for everyone; lifestyle is community-specific."},
    {"Place":"Scottsdale", "State":"Arizona", "Type":"Desert / Golf / Luxury", "Affordability":50, "Healthcare":84, "Lifestyle":94, "Climate":78, "Golf":98, "Why":"World-class golf, strong healthcare, luxury amenities.", "Watch-outs":"High housing costs and very hot summers."},
    {"Place":"Pinehurst", "State":"North Carolina", "Type":"Golf / Village", "Affordability":72, "Healthcare":76, "Lifestyle":86, "Climate":78, "Golf":98, "Why":"One of the strongest golf-retirement destinations in the country.", "Watch-outs":"Smaller-town feel; healthcare may require regional access."},
    {"Place":"Knoxville", "State":"Tennessee", "Type":"University / Mountains", "Affordability":82, "Healthcare":78, "Lifestyle":80, "Climate":74, "Golf":76, "Why":"No state income tax, access to mountains, lower cost of living.", "Watch-outs":"No beach lifestyle; humid summers."},
    {"Place":"Greenville", "State":"South Carolina", "Type":"Small City / Mountains Nearby", "Affordability":77, "Healthcare":78, "Lifestyle":84, "Climate":78, "Golf":78, "Why":"Vibrant downtown, lower cost, strong lifestyle balance.", "Watch-outs":"Rapid growth can pressure housing affordability."},
    {"Place":"Traverse City", "State":"Michigan", "Type":"Lake / Summer Lifestyle", "Affordability":58, "Healthcare":72, "Lifestyle":88, "Climate":55, "Golf":82, "Why":"Excellent summer lifestyle, water, wineries, golf, Michigan ties.", "Watch-outs":"Winter climate and seasonal tourism pressure."},
    {"Place":"Grand Rapids", "State":"Michigan", "Type":"Mid-size City / Healthcare", "Affordability":73, "Healthcare":84, "Lifestyle":74, "Climate":54, "Golf":72, "Why":"Strong healthcare, reasonable cost, close to west Michigan lifestyle.", "Watch-outs":"Cold winters; not a beach retirement year-round."},
    {"Place":"Chattanooga", "State":"Tennessee", "Type":"River City / Outdoors", "Affordability":80, "Healthcare":75, "Lifestyle":82, "Climate":74, "Golf":74, "Why":"Scenic river/mountain setting, lower taxes, outdoor lifestyle.", "Watch-outs":"Healthcare depth and humidity should be reviewed."},
]


def estimate_state_tax(row):
    income = guaranteed_income() + max(0, annual_spending() - guaranteed_income())
    tax_sensitivity = (100 - row["Tax"]) / 100
    return income * tax_sensitivity * 0.08


def state_score(row, weights):
    return (
        row["Tax"] * weights["Tax"] +
        row["Cost"] * weights["Cost"] +
        row["Healthcare"] * weights["Healthcare"] +
        row["Lifestyle"] * weights["Lifestyle"] +
        row["Climate"] * weights["Climate"] +
        row["Golf"] * weights["Golf"]
    ) / sum(weights.values())


def place_score(row, weights):
    # Place-level data has no separate tax score, so borrow state tax/cost context.
    state_row = next(s for s in STATE_DATA if s["State"] == row["State"])
    return (
        state_row["Tax"] * weights["Tax"] +
        row["Affordability"] * weights["Cost"] +
        row["Healthcare"] * weights["Healthcare"] +
        row["Lifestyle"] * weights["Lifestyle"] +
        row["Climate"] * weights["Climate"] +
        row["Golf"] * weights["Golf"]
    ) / sum(weights.values())


def show_phase4():
    st.title("Phase 4 — Lifestyle & Best Places to Retire")
    st.write("Compare states and places based on taxes, cost, healthcare, climate, golf/recreation, lifestyle fit, and your personal priorities.")
    section_guide(
        "Phase 4 — Lifestyle & Best Places to Retire",
        "Adjust the priority sliders to tell the app what matters most: taxes, cost of living, healthcare, lifestyle, climate, and golf/recreation. Then review state rankings, place details, and state-to-state comparisons.",
        "It creates a personalized location score and helps compare where retirement may be more affordable, enjoyable, or practical based on your preferences.",
        "Use this as a short-listing tool. Before moving, users should still verify local housing costs, insurance, healthcare networks, and tax rules."
    )
    st.markdown("<div class='soft-box'>This is where the retirement plan becomes personal. A financially possible retirement should also fit the life you actually want.</div>", unsafe_allow_html=True)

    st.subheader("What matters most to you?")
    c1, c2, c3 = st.columns(3)
    w_tax = c1.slider("Tax importance", 1, 10, 8, key="p4_tax_weight", help="How important low retirement taxes are in your location ranking. Higher means taxes matter more.")
    w_cost = c2.slider("Cost of living importance", 1, 10, 7, key="p4_cost_weight", help="How important affordable housing, everyday expenses, and general cost of living are to you.")
    w_health = c3.slider("Healthcare importance", 1, 10, 8, key="p4_health_weight", help="How important healthcare access and quality are in your retirement location ranking.")
    c4, c5, c6 = st.columns(3)
    w_life = c4.slider("Lifestyle importance", 1, 10, 8, key="p4_lifestyle_weight", help="How important restaurants, culture, community, recreation, and overall lifestyle fit are.")
    w_climate = c5.slider("Climate importance", 1, 10, 7, key="p4_climate_weight", help="How important weather, warmth, winter avoidance, and seasonal comfort are.")
    w_golf = c6.slider("Golf / recreation importance", 1, 10, 7, key="p4_golf_weight", help="How important golf access, outdoor activities, clubs, parks, and recreation are.")

    weights = {"Tax": w_tax, "Cost": w_cost, "Healthcare": w_health, "Lifestyle": w_life, "Climate": w_climate, "Golf": w_golf}

    c1, c2, c3 = st.columns(3)
    preferred = c1.multiselect("Preferred states, optional", [s["State"] for s in STATE_DATA], default=[], key="p4_preferred", help="Optional boost for states you already like or want to prioritize.")
    avoid = c2.multiselect("States to avoid, optional", [s["State"] for s in STATE_DATA], default=[], key="p4_avoid", help="Optional list of states you do not want recommended.")
    snowbird = c3.checkbox("Interested in snowbird strategy?", value=True, key="p4_snowbird", help="Check this if you might keep one home base and spend winters in a warmer state.")

    states = pd.DataFrame(STATE_DATA)
    states = states[~states["State"].isin(avoid)].copy()
    states["Personalized Score"] = states.apply(lambda r: state_score(r, weights), axis=1)
    if preferred:
        states.loc[states["State"].isin(preferred), "Personalized Score"] += 3
    states["Estimated Annual State/Local Tax"] = states.apply(estimate_state_tax, axis=1)
    states = states.sort_values("Personalized Score", ascending=False).reset_index(drop=True)

    top_state = states.iloc[0]
    st.markdown(f"<div class='success-box'>Top state fit: <b>{top_state['State']}</b> with a personalized score of <b>{top_state['Personalized Score']:.0f}/100</b>.</div>", unsafe_allow_html=True)

    fig = go.Figure()
    top10 = states.head(10).sort_values("Personalized Score")
    fig.add_trace(go.Bar(y=top10["State"], x=top10["Personalized Score"], orientation="h", text=top10["Personalized Score"].round(0)))
    fig.update_layout(height=420, title="Top Retirement States — Personalized Score", xaxis_title="Score", margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    state_display = states[["State", "Personalized Score", "Tax", "Cost", "Healthcare", "Lifestyle", "Climate", "Golf", "Estimated Annual State/Local Tax", "Places", "Watch-outs"]].copy()
    state_display["Personalized Score"] = state_display["Personalized Score"].round(0).astype(int)
    state_display["Estimated Annual State/Local Tax"] = state_display["Estimated Annual State/Local Tax"].apply(money)
    st.subheader("State Comparison Table")
    st.dataframe(state_display, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("City / Place-Level Recommendations")
    filter_states = st.multiselect("Filter places by state", [s["State"] for s in STATE_DATA], default=[], key="p4_place_filter", help="Limit city/place recommendations to selected states, or leave blank to compare all available places.")
    places = pd.DataFrame(PLACE_DATA)
    if filter_states:
        places = places[places["State"].isin(filter_states)].copy()
    places["Recommended Fit Score"] = places.apply(lambda r: place_score(r, weights), axis=1)
    places = places.sort_values("Recommended Fit Score", ascending=False).reset_index(drop=True)
    top_place = places.iloc[0]
    st.markdown(f"<div class='success-box'>Top place match: <b>{top_place['Place']}, {top_place['State']}</b> with a fit score of <b>{top_place['Recommended Fit Score']:.0f}/100</b>.</div>", unsafe_allow_html=True)

    fig2 = go.Figure()
    top_places = places.head(10).sort_values("Recommended Fit Score")
    fig2.add_trace(go.Bar(y=top_places["Place"] + ", " + top_places["State"], x=top_places["Recommended Fit Score"], orientation="h", text=top_places["Recommended Fit Score"].round(0)))
    fig2.update_layout(height=430, title="Top Places to Retire — Personalized Fit", xaxis_title="Fit Score", margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig2, use_container_width=True)

    place_display = places[["Place", "State", "Type", "Recommended Fit Score", "Affordability", "Healthcare", "Lifestyle", "Climate", "Golf", "Why", "Watch-outs"]].copy()
    place_display["Recommended Fit Score"] = place_display["Recommended Fit Score"].round(0).astype(int)
    st.dataframe(place_display, use_container_width=True, hide_index=True)

    st.subheader("Place Detail")
    choice = st.selectbox("Choose a place to review", (places["Place"] + ", " + places["State"]).tolist(), key="p4_place_detail", help="Pick a specific city/community to see score details, strengths, and watch-outs.")
    selected = places[(places["Place"] + ", " + places["State"]) == choice].iloc[0]
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Fit Score", f"{selected['Recommended Fit Score']:.0f}/100")
    d2.metric("Affordability", f"{selected['Affordability']}/100")
    d3.metric("Healthcare", f"{selected['Healthcare']}/100")
    d4.metric("Lifestyle", f"{selected['Lifestyle']}/100")
    d5.metric("Golf / Rec", f"{selected['Golf']}/100")
    c1, c2 = st.columns(2)
    c1.markdown(f"**Why retire here**\n\n{selected['Why']}")
    c2.markdown(f"**Watch-outs**\n\n{selected['Watch-outs']}")
    st.markdown(f"**Community type:** {selected['Type']}")

    st.divider()
    st.subheader("State-to-State Comparison")
    default_compare = ["Michigan", "Florida", "South Carolina"]
    compare = st.multiselect("Choose states to compare", [s["State"] for s in STATE_DATA], default=default_compare, key="p4_state_compare", help="Select states for a side-by-side comparison of taxes, costs, healthcare, climate, lifestyle, and watch-outs.")
    compare_df = states[states["State"].isin(compare)].copy()
    if not compare_df.empty:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=compare_df["State"], y=compare_df["Personalized Score"], name="Personalized Score"))
        fig3.add_trace(go.Bar(x=compare_df["State"], y=compare_df["Tax"], name="Tax Score"))
        fig3.update_layout(barmode="group", height=360, title="Base vs Personalized Retirement Fit")
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(compare_df[["State", "Personalized Score", "Tax", "Cost", "Healthcare", "Lifestyle", "Climate", "Golf", "Watch-outs"]], use_container_width=True, hide_index=True)

    if snowbird:
        st.markdown("<div class='warn-box'><b>Snowbird idea:</b> Consider keeping Michigan as your home base while testing 1–3 months in Florida, South Carolina, Arizona, or Tennessee before buying. This avoids making a permanent move before confirming lifestyle, healthcare, taxes, and insurance reality.</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='success-box'><b>Plain-English recommendation:</b> Based on your priorities, start deeper research with <b>{top_place['Place']}, {top_place['State']}</b> and compare it against your current Michigan lifestyle. The next step is to verify housing cost, property taxes, insurance, healthcare networks, and how it feels during both peak and off-season months.</div>", unsafe_allow_html=True)



def build_recommendations():
    score = readiness_score()
    spend = annual_spending()
    income = guaranteed_income()
    gap = max(0, spend - income)
    portfolio = max(portfolio_total(), 1)
    withdrawal_rate = gap / portfolio * 100
    recs = []
    if score < 60:
        recs.append("Improve the foundation first: reduce retirement spending, delay retirement, increase savings, or add guaranteed income.")
    else:
        recs.append("Your foundation is moving in the right direction. Focus next on tax strategy, healthcare bridge planning, and stress testing.")
    if withdrawal_rate > 5:
        recs.append("Portfolio withdrawal pressure looks high. Test a lower monthly spending target or a later retirement age in the Retirement Lab.")
    elif withdrawal_rate > 4:
        recs.append("Withdrawal pressure is moderate. Stress test early market downturns before relying on this plan.")
    else:
        recs.append("Withdrawal pressure appears reasonable using this simplified model. Keep validating with taxes, inflation, and healthcare costs.")
    if st.session_state.retire_age < 65:
        recs.append("Because retirement is before Medicare, build a healthcare bridge estimate and keep a dedicated cash/bond buffer.")
    if st.session_state.traditional > st.session_state.roth * 3:
        recs.append("Traditional pre-tax balances are much larger than Roth balances. Explore Roth conversion windows before RMD age.")
    if st.session_state.spouse_enabled:
        recs.append("Because a spouse is included, eventually model survivor income, Social Security timing, and the widow/widower tax risk.")
    return recs[:5]


def current_plan_snapshot():
    score = readiness_score()
    income = guaranteed_income()
    spend = annual_spending()
    portfolio = portfolio_total()
    gap = max(0, spend - income)
    return {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "plan_name": st.session_state.get("p5_plan_name", st.session_state.plan_name),
        "retirement_age": int(st.session_state.retire_age),
        "planning_horizon": int(st.session_state.plan_age),
        "readiness_score": int(score),
        "confidence": confidence_label(score),
        "annual_spending": float(spend),
        "guaranteed_income": float(income),
        "portfolio": float(portfolio),
        "portfolio_gap": float(gap),
        "withdrawal_rate": float(gap / max(portfolio, 1) * 100),
        "home_equity": float(st.session_state.home_equity),
        "bucket1_balance": float(st.session_state.get("bucket1_balance", 0)),
        "bucket2_balance": float(st.session_state.get("bucket2_balance", 0)),
        "bucket1_return": float(st.session_state.get("bucket1_return", 0)),
        "bucket2_return": float(st.session_state.get("bucket2_return", 0)),
        "bucket_blended_return": float(bucket_blended_return()),
        "spouse_included": bool(st.session_state.spouse_enabled),
        "notes": st.session_state.get("p5_notes", ""),
        "tags": st.session_state.get("p5_tags", []),
        "recommendations": build_recommendations(),
        "inputs": capture_plan_inputs(),
    }


def show_phase5():
    st.title("Phase 5 — My Plans")
    st.write("Turn your inputs into a saved retirement blueprint with notes, assumptions, action steps, and next-best recommendations.")
    section_guide(
        "Phase 5 — My Plans",
        "Name your plan, add notes and tags, review recommendations, complete checklist items, then save or export your plan for later.",
        "This phase turns the analysis into an action plan. It captures your current assumptions, readiness score, recommendations, notes, and saved plan versions.",
        "Create separate plans for major choices, such as Retire at 58, Retire at 62, Florida Snowbird, Downsize, or Conservative Market Case."
    )
    st.markdown("<div class='soft-box'>This version saves plans locally during your current browser session. Once the app is stable, we can add login and permanent database saving.</div>", unsafe_allow_html=True)

    score = readiness_score()
    income = guaranteed_income()
    spend = annual_spending()
    portfolio = portfolio_total()
    gap = max(0, spend - income)
    withdrawal_rate = gap / max(portfolio, 1) * 100

    st.subheader("Current Blueprint Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Readiness Score", f"{score}/100", confidence_label(score))
    c2.metric("Target Retirement", f"Age {st.session_state.retire_age}")
    c3.metric("Annual Spending", money(spend))
    c4.metric("Withdrawal Rate", f"{withdrawal_rate:.1f}%")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Guaranteed Income", "Portfolio Gap"], y=[income, gap], text=[money(income), money(gap)], textposition="auto"))
    fig.update_layout(height=330, title="How Your Annual Retirement Spending Is Covered", yaxis_tickprefix="$", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Plan Details")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.text_input("Plan name", key="p5_plan_name", value=st.session_state.get("p5_plan_name", st.session_state.plan_name), help="Name this saved blueprint so you can identify it later, such as Retire at 60 or South Carolina Snowbird Plan.")
        st.multiselect("Plan tags", ["Base Plan", "Conservative", "Aggressive", "Early Retirement", "Snowbird", "Downsize", "Tax Focus", "Healthcare Focus"], default=st.session_state.get("p5_tags", ["Base Plan"]), key="p5_tags", help="Optional labels to organize saved plans by strategy or theme.")
    with c2:
        st.text_area("Plan notes", key="p5_notes", placeholder="Example: Retire at 60, delay Social Security to 67, test South Carolina snowbird lifestyle, reduce spending after 70...", help="Optional notes about this version of your plan, tradeoffs, assumptions, or follow-up questions.")

    st.subheader("Recommended Next Steps")
    recs = build_recommendations()
    for i, rec in enumerate(recs, start=1):
        st.markdown(f"**{i}.** {rec}")

    st.subheader("Action Checklist")
    left, right = st.columns(2)
    with left:
        st.checkbox("Confirm Social Security estimate from SSA.gov", key="p5_check_ss")
        st.checkbox("Complete detailed monthly budget", key="p5_check_budget")
        st.checkbox("Estimate healthcare bridge costs before Medicare", key="p5_check_healthcare")
        st.checkbox("Compare at least three retirement ages", key="p5_check_ages")
    with right:
        st.checkbox("Review Roth conversion opportunity", key="p5_check_roth")
        st.checkbox("Compare at least three retirement locations", key="p5_check_locations")
        st.checkbox("Stress test bad first 3 years of market returns", key="p5_check_stress")
        st.checkbox("Discuss plan with a qualified financial/tax professional", key="p5_check_pro")

    checks = ["p5_check_ss", "p5_check_budget", "p5_check_healthcare", "p5_check_ages", "p5_check_roth", "p5_check_locations", "p5_check_stress", "p5_check_pro"]
    completed = sum(1 for k in checks if st.session_state.get(k))
    st.progress(completed / len(checks), text=f"Blueprint completion checklist: {completed} of {len(checks)} completed")

    st.divider()
    st.subheader("Save, Load, Export, and Import")
    st.markdown("<div class='soft-box'>This is still local saving only. Plans stay available while the browser session is active. Export a plan file if you want to keep it and import it later.</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1])
    if c1.button("Save current plan", use_container_width=True, help="Saves the current inputs and assumptions into this browser session."):
        snap = current_plan_snapshot()
        st.session_state.saved_plans.append(snap)
        st.success(f"Saved: {snap['plan_name']}")
    if c2.button("Clear saved plans", use_container_width=True, help="Clears all locally saved plans from this browser session."):
        st.session_state.saved_plans = []
        st.warning("Saved plans cleared for this session.")

    snapshot = current_plan_snapshot()
    c3.download_button(
        "Export current plan",
        data=json.dumps(snapshot, indent=2),
        file_name=f"{snapshot['plan_name'].replace(' ', '_').lower()}_retirement_blueprint.json",
        mime="application/json",
        use_container_width=True,
        help="Downloads the current plan as a JSON file you can import later.",
    )

    if st.session_state.get("last_loaded_plan"):
        st.success(f"Loaded plan: {st.session_state.last_loaded_plan}")
    if st.session_state.get("last_import_status"):
        st.info(st.session_state.last_import_status)

    st.subheader("Import a Plan File")
    upload = st.file_uploader(
        "Upload exported retirement blueprint JSON",
        type=["json"],
        help="Use this to bring back a plan you previously exported from this app.",
    )
    if upload is not None:
        try:
            payload = json.loads(upload.getvalue().decode("utf-8"))
            st.button(
                "Import plan file",
                use_container_width=True,
                on_click=import_plan_payload,
                args=(payload,),
                help="Adds the uploaded plan to your local saved plans and loads its inputs when available.",
            )
        except Exception as e:
            st.error(f"Could not read this JSON file: {e}")

    st.subheader("Saved Plans This Session")
    if not st.session_state.saved_plans:
        st.info("No saved plans yet. Save your current blueprint above.")
    else:
        rows = []
        for idx, plan in enumerate(st.session_state.saved_plans, start=1):
            rows.append({
                "#": idx,
                "Plan": plan.get("plan_name", "Saved Plan"),
                "Saved": plan.get("saved_at", ""),
                "Retire Age": plan.get("retirement_age", ""),
                "Score": plan.get("readiness_score", ""),
                "Confidence": plan.get("confidence", ""),
                "Annual Spending": money(plan.get("annual_spending", 0)),
                "Portfolio": money(plan.get("portfolio", 0)),
                "Withdrawal Rate": f"{float(plan.get('withdrawal_rate', 0)):.1f}%",
                "Tags": ", ".join(plan.get("tags", [])),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("### Plan Manager")
        for idx, plan in enumerate(st.session_state.saved_plans):
            with st.container(border=True):
                top = st.columns([2, 1, 1, 1])
                top[0].markdown(f"**{plan.get('plan_name', 'Saved Plan')}**  \n<span class='small-muted'>Saved {plan.get('saved_at', '')} • {plan.get('confidence', '')} • Score {plan.get('readiness_score', '')}/100</span>", unsafe_allow_html=True)
                top[1].metric("Retire", f"Age {plan.get('retirement_age', '')}")
                top[2].metric("Spend", money(plan.get("annual_spending", 0)))
                top[3].metric("Portfolio", money(plan.get("portfolio", 0)))

                b1, b2, b3 = st.columns([1, 1, 1])
                b1.button(
                    "Load plan",
                    key=f"load_plan_{idx}",
                    use_container_width=True,
                    on_click=load_saved_plan,
                    args=(idx,),
                    help="Loads this saved plan's inputs back into the app.",
                )
                b2.download_button(
                    "Export",
                    data=json.dumps(plan, indent=2),
                    file_name=f"{plan.get('plan_name', 'saved_plan').replace(' ', '_').lower()}_retirement_blueprint.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"export_plan_{idx}",
                    help="Downloads only this saved plan.",
                )
                b3.button(
                    "Delete",
                    key=f"delete_plan_{idx}",
                    use_container_width=True,
                    on_click=delete_saved_plan,
                    args=(idx,),
                    help="Deletes this saved plan from the current session.",
                )

                with st.expander("View notes and recommendations"):
                    st.write(plan.get("notes") or "No notes added.")
                    for rec in plan.get("recommendations", []):
                        st.write(f"• {rec}")

        all_payload = {
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "app": "Retirement Blueprint 101",
            "saved_plans": st.session_state.saved_plans,
        }
        st.download_button(
            "Export all saved plans",
            data=json.dumps(all_payload, indent=2),
            file_name="retirement_blueprint_all_saved_plans.json",
            mime="application/json",
            use_container_width=True,
            help="Downloads every plan saved in this browser session.",
        )


def build_report_html():
    snapshot = current_plan_snapshot()
    rec_items = "".join(f"<li>{r}</li>" for r in snapshot.get("recommendations", []))
    spouse_text = "Yes" if snapshot.get("spouse_included") else "No"
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Retirement Blueprint 101 Report</title>
<style>
body {{ font-family: Arial, sans-serif; color:#111827; margin:40px; line-height:1.45; }}
h1 {{ color:#061A3A; }}
h2 {{ color:#061A3A; margin-top:28px; }}
.card {{ border:1px solid #e5e7eb; border-radius:14px; padding:18px; margin:14px 0; }}
.grid {{ display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:14px; }}
.metric {{ font-size:28px; font-weight:800; }}
.muted {{ color:#64748b; }}
</style>
</head>
<body>
<h1>Retirement Blueprint 101 Report</h1>
<p class="muted">Generated {snapshot['saved_at']}</p>
<div class="grid">
  <div class="card"><div>Plan Name</div><div class="metric">{snapshot['plan_name']}</div></div>
  <div class="card"><div>Confidence</div><div class="metric">{snapshot['confidence']}</div></div>
  <div class="card"><div>Readiness Score</div><div class="metric">{snapshot['readiness_score']}/100</div></div>
  <div class="card"><div>Target Retirement Age</div><div class="metric">{snapshot['retirement_age']}</div></div>
</div>
<h2>Core Numbers</h2>
<ul>
  <li>Annual spending: {money(snapshot['annual_spending'])}</li>
  <li>Guaranteed income: {money(snapshot['guaranteed_income'])}</li>
  <li>Portfolio: {money(snapshot['portfolio'])}</li>
  <li>Portfolio gap: {money(snapshot['portfolio_gap'])}</li>
  <li>Withdrawal rate: {snapshot['withdrawal_rate']:.1f}%</li>
  <li>Home equity: {money(snapshot['home_equity'])}</li>
  <li>Spouse included: {spouse_text}</li>
</ul>
<h2>Recommended Next Steps</h2>
<ol>{rec_items}</ol>
<h2>Notes</h2>
<p>{snapshot.get('notes') or 'No notes added yet.'}</p>
<p class="muted">Educational estimate only. Not individualized financial, legal, or tax advice.</p>
</body>
</html>
"""


def show_reports():
    st.title("Reports")
    st.write("Create a simple retirement blueprint report that summarizes your dashboard, Phase 1 inputs, Phase 2 retirement timing, Phase 3 income/tax picture, Phase 4 lifestyle priorities, and Phase 5 action plan.")
    section_guide(
        "Reports",
        "Use this page after entering your inputs and testing scenarios. Review the executive summary, recommendations, and projection table, then download the report or data files.",
        "It gives users a simple snapshot they can save, share with a spouse, or bring to a financial/tax professional.",
        "The report is only as accurate as the inputs. Encourage users to update assumptions before relying on the summary."
    )
    st.markdown("<div class='soft-box'>This report is local to your session for now. Later we can add branded PDFs, advisor-ready reports, and permanent saved report history.</div>", unsafe_allow_html=True)

    snapshot = current_plan_snapshot()
    projection_df = pd.DataFrame(project_portfolio())

    st.subheader("Report Preview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Readiness Score", f"{snapshot['readiness_score']}/100")
    c2.metric("Confidence", snapshot["confidence"])
    c3.metric("Retirement Age", f"Age {snapshot['retirement_age']}")
    c4.metric("Withdrawal Rate", f"{snapshot['withdrawal_rate']:.1f}%")

    st.subheader("Executive Summary")
    st.write(f"Your current plan targets retirement at age **{snapshot['retirement_age']}** and plans through age **{snapshot['planning_horizon']}**. Based on the current inputs, the simplified readiness score is **{snapshot['readiness_score']}/100** with a confidence level of **{snapshot['confidence']}**.")
    st.write(f"Estimated annual spending is **{money(snapshot['annual_spending'])}**. Guaranteed income covers **{money(snapshot['guaranteed_income'])}**, leaving an estimated portfolio gap of **{money(snapshot['portfolio_gap'])}** per year before taxes and detailed timing adjustments.")

    st.subheader("Recommendation Summary")
    for i, rec in enumerate(snapshot.get("recommendations", []), start=1):
        st.markdown(f"**{i}.** {rec}")

    st.subheader("Projection Table")
    projection_view = projection_df.copy()
    projection_view["Portfolio"] = projection_view["Portfolio"].map(lambda x: money(x))
    projection_view["Withdrawal"] = projection_view["Withdrawal"].map(lambda x: money(x))
    st.dataframe(projection_view, use_container_width=True, hide_index=True)

    st.subheader("Downloads")
    report_html = build_report_html()
    csv_data = projection_df.to_csv(index=False)
    json_data = json.dumps(snapshot, indent=2)

    d1, d2, d3 = st.columns(3)
    d1.download_button("Download HTML Report", data=report_html, file_name="retirement_blueprint_report.html", mime="text/html", use_container_width=True)
    d2.download_button("Download Projection CSV", data=csv_data, file_name="retirement_projection.csv", mime="text/csv", use_container_width=True)
    d3.download_button("Download Plan JSON", data=json_data, file_name="retirement_blueprint_plan.json", mime="application/json", use_container_width=True)

    with st.expander("What this report includes"):
        st.write("This report currently includes your core score, retirement age, spending, guaranteed income, portfolio gap, withdrawal rate, key recommendations, and a projection table. Future versions can add branded PDF export, tax schedules, Roth conversion summaries, and advisor-ready scenario comparisons.")




def plan_context_for_ai():
    """Create a compact, non-sensitive summary of the user's current plan for the AI coach."""
    score = readiness_score()
    context = {
        "plan_name": st.session_state.get("plan_name"),
        "current_age": st.session_state.get("age"),
        "target_retirement_age": st.session_state.get("retire_age"),
        "planning_horizon_age": st.session_state.get("plan_age"),
        "annual_household_income": st.session_state.get("current_income"),
        "annual_spending_estimate": annual_spending(),
        "monthly_spending_estimate": st.session_state.get("monthly_spending"),
        "portfolio_total": portfolio_total(),
        "traditional_balance": st.session_state.get("traditional"),
        "roth_balance": st.session_state.get("roth"),
        "taxable_cash_balance": st.session_state.get("taxable_cash"),
        "hsa_balance": st.session_state.get("hsa_balance"),
        "home_equity": st.session_state.get("home_equity"),
        "mortgage": st.session_state.get("mortgage"),
        "annual_social_security_fra_estimate": st.session_state.get("social_security"),
        "social_security_start_age": st.session_state.get("ss_start_age"),
        "social_security_full_retirement_age": st.session_state.get("ss_fra_age"),
        "annual_social_security_adjusted": adjusted_user_social_security(),
        "pension_income": st.session_state.get("pension_income"),
        "other_income": st.session_state.get("other_income"),
        "spouse_included": st.session_state.get("spouse_enabled"),
        "spouse_age": st.session_state.get("spouse_age") if st.session_state.get("spouse_enabled") else None,
        "spouse_social_security_fra_estimate": st.session_state.get("spouse_ss") if st.session_state.get("spouse_enabled") else None,
        "spouse_social_security_adjusted": adjusted_spouse_social_security() if st.session_state.get("spouse_enabled") else None,
        "bucket1_balance": st.session_state.get("bucket1_balance"),
        "bucket1_return": st.session_state.get("bucket1_return"),
        "bucket2_balance": st.session_state.get("bucket2_balance"),
        "bucket2_return": st.session_state.get("bucket2_return"),
        "blended_bucket_return": round(bucket_blended_return(), 2),
        "filing_status": st.session_state.get("filing_status"),
        "estimated_tax_rate": st.session_state.get("tax_rate"),
        "aca_sensitive": st.session_state.get("aca_sensitive"),
        "rule55_eligible": st.session_state.get("rule55_eligible"),
        "readiness_score": score,
        "confidence": confidence_label(score),
    }
    return context


def local_ai_coach_response(question):
    """Rule-based fallback when no OpenAI key is configured."""
    score = readiness_score()
    gap = max(0, annual_spending() - guaranteed_income())
    withdrawal_rate = gap / max(portfolio_total(), 1) * 100
    ideas = []

    if withdrawal_rate > 5:
        ideas.append("Your estimated portfolio withdrawal need looks elevated. Phase 2 can test delaying retirement, lowering spending, or increasing guaranteed income.")
    else:
        ideas.append("Your estimated first-year withdrawal need appears more manageable based on the current inputs.")

    if st.session_state.get("aca_sensitive") and st.session_state.age < 65:
        ideas.append("Because healthcare before Medicare may matter, be careful with taxable income in the bridge years and test ACA-sensitive scenarios in Phase 3.")

    if float(st.session_state.get("traditional", 0)) > float(st.session_state.get("roth", 0)) * 3:
        ideas.append("You have much more traditional money than Roth money. That can make Roth conversion years worth exploring before RMD age.")

    if st.session_state.retire_age < 65:
        ideas.append("Retiring before Medicare creates a healthcare bridge period. Make sure Phase 2 includes healthcare costs from retirement age to 65.")

    if not ideas:
        ideas.append("Your plan does not show an obvious red flag from the high-level inputs, but it is still worth stress-testing returns, taxes, and spending flexibility.")

    return "\n\n".join([
        "**AI Coach preview — no API key connected yet**",
        f"Based on the current plan, your readiness score is **{score}/100** and the estimated first-year portfolio withdrawal rate is about **{withdrawal_rate:.1f}%**.",
        "\n".join([f"- {idea}" for idea in ideas]),
        "This is educational guidance only, not financial, tax, or legal advice."
    ])


def call_openai_coach(question, context):
    """Call OpenAI only when OPENAI_API_KEY is available in Streamlit secrets."""
    from openai import OpenAI

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    model = st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")

    system_prompt = """
You are the AI Coach inside Retirement Blueprint 101, an educational retirement planning app.
You are not a CFP, CPA, attorney, or fiduciary. Do not claim to provide personalized financial, tax, legal, or investment advice.
Use plain English for adults 50+.
Use the user's current app inputs as context, but treat all calculations as estimates.
Give practical next steps and point users to app phases: Phase 1 Foundation, Phase 2 Retirement Lab, Phase 3 Income & Tax, Phase 4 Lifestyle, Phase 5 My Plans.
Do not recommend specific securities, market timing, or guaranteed returns.
When taxes, Roth conversions, ACA, RMDs, Social Security, or Rule of 55 are involved, remind the user to verify with a qualified professional.
Keep answers concise, structured, and action-oriented.
"""

    user_prompt = f"""
Current retirement plan context:
{json.dumps(context, indent=2)}

User question:
{question}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=700,
    )
    return response.choices[0].message.content


def show_ai_coach():
    st.title("AI Coach")
    section_guide(
        "AI Coach",
        "Ask plain-English questions about your current retirement plan. The coach uses the inputs from your dashboard and phases to explain trade-offs, risks, and next steps.",
        "It can summarize your plan, highlight risk areas, suggest which phase to revisit, explain taxes/withdrawals in plain English, and help you think through retirement timing or lifestyle trade-offs.",
        "Use it as an educational planning assistant, not as a replacement for a CFP, CPA, attorney, or fiduciary advisor."
    )

    st.info("The AI Coach is educational only. It does not provide personalized financial, tax, legal, or investment advice.")

    context = plan_context_for_ai()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Readiness Score", f"{context['readiness_score']}/100")
    c2.metric("Confidence", context["confidence"])
    c3.metric("Portfolio", money(context["portfolio_total"]))
    c4.metric("Annual Spending", money(context["annual_spending_estimate"]))

    st.markdown("### Suggested questions")
    qcols = st.columns(2)
    examples = [
        "What are the biggest risks in my current retirement plan?",
        "Should I focus more on reducing spending or delaying retirement?",
        "How should I think about Roth conversions before RMD age?",
        "What should I review before retiring before Medicare?",
        "What does my two-bucket strategy tell me?",
        "Which phase of the app should I work on next?",
    ]
    for i, example in enumerate(examples):
        with qcols[i % 2]:
            if st.button(example, key=f"ai_example_{i}"):
                st.session_state["ai_question"] = example

    st.markdown("### Ask your coach")
    question = st.text_area(
        "Your question",
        key="ai_question",
        height=120,
        placeholder="Example: Can I retire at 58, and what would make the plan safer?",
        help="Ask about your plan, retirement timing, taxes, withdrawals, Roth conversions, Social Security, healthcare bridge years, or lifestyle trade-offs."
    )

    col_a, col_b = st.columns([1, 3])
    with col_a:
        ask = st.button("Ask AI Coach", type="primary")
    with col_b:
        has_key = bool(st.secrets.get("OPENAI_API_KEY")) if hasattr(st, "secrets") else False
        if has_key:
            st.caption("Connected to OpenAI through Streamlit Secrets.")
        else:
            st.caption("No OpenAI key connected yet. The app will show a rule-based coach preview.")

    if ask:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            with st.spinner("Reviewing your retirement blueprint..."):
                try:
                    if has_key:
                        answer = call_openai_coach(question, context)
                    else:
                        answer = local_ai_coach_response(question)
                    st.session_state.setdefault("ai_history", []).append({
                        "question": question,
                        "answer": answer,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    })
                except Exception as e:
                    st.error(f"AI Coach error: {e}")
                    st.caption("Check OPENAI_API_KEY in Streamlit Secrets and make sure openai is listed in requirements.txt.")

    if st.session_state.get("ai_history"):
        st.markdown("### Coach conversation")
        for item in reversed(st.session_state["ai_history"][-5:]):
            with st.expander(f"Q: {item['question'][:90]}", expanded=True):
                st.markdown(f"**Asked:** {item['time']}")
                st.markdown(item["answer"])

    st.markdown("### Setup notes")
    with st.expander("How to connect the real OpenAI API", expanded=False):
        st.markdown("""
1. Add `openai` to `requirements.txt`.
2. In Streamlit Cloud, open your app settings and add a secret named `OPENAI_API_KEY`.
3. Optional: add `OPENAI_MODEL = "gpt-4o-mini"` or another model you have access to.
4. Reboot the app.

Keep the API key in Streamlit Secrets only. Do not paste it into GitHub.
""")



def show_resources():
    st.title("Resources")
    section_guide(
        "Resources",
        "Use this page as the plain-English learning center for retirement concepts. It helps users understand what each strategy means before they use the tools.",
        "It explains retirement terms, planning rules, Social Security, taxes, Roth conversions, healthcare bridge years, bucket strategy, withdrawal planning, and lifestyle/location planning.",
        "When a user feels unsure about a term or strategy, send them here first. This section builds trust and lowers confusion."
    )

    st.markdown("<div class='soft-box'>Educational content only. These resources help explain concepts so users can have better conversations with qualified financial, tax, legal, or healthcare professionals.</div>", unsafe_allow_html=True)

    search = st.text_input(
        "Search resources",
        placeholder="Try: Roth conversion, Rule of 55, RMD, bucket strategy, Social Security...",
        help="Search is a simple guide for now. Future versions can filter the glossary and articles dynamically."
    )

    tabs = st.tabs([
        "Start Here",
        "Glossary",
        "Retirement Rules",
        "Taxes & Withdrawals",
        "Healthcare",
        "Lifestyle",
        "Checklists",
    ])

    with tabs[0]:
        st.subheader("Start Here: How to Use Retirement Blueprint 101")
        st.write("The app is organized like a guided retirement journey. Start with basic inputs, then go deeper only where needed.")
        journey = pd.DataFrame([
            {"Step": "Dashboard", "Purpose": "Quick snapshot", "What to do": "Review your score, income estimate, risks, and next steps."},
            {"Step": "Phase 1 — Foundation", "Purpose": "Build your base plan", "What to do": "Enter age, retirement age, income, spending, assets, debts, Social Security, and spouse details."},
            {"Step": "Phase 2 — Retirement Lab", "Purpose": "Test what-if scenarios", "What to do": "Compare retirement ages, return assumptions, spending levels, and two-bucket strategy."},
            {"Step": "Phase 3 — Income & Tax", "Purpose": "Improve withdrawal efficiency", "What to do": "Review income sources, tax estimate, Roth conversion opportunity, RMD risk, and withdrawal order."},
            {"Step": "Phase 4 — Lifestyle", "Purpose": "Design retirement life", "What to do": "Compare states, lifestyle priorities, best places to retire, and snowbird options."},
            {"Step": "Phase 5 — My Plans", "Purpose": "Organize your blueprint", "What to do": "Save plans, compare ideas, track checklist items, and export your plan."},
        ])
        st.dataframe(journey, use_container_width=True, hide_index=True)

        st.markdown("### Suggested path")
        st.markdown("""
1. Enter your best estimates in Phase 1.  
2. Use Phase 2 to test retirement ages and return assumptions.  
3. Use Phase 3 to understand taxes and withdrawal order.  
4. Use Phase 4 to compare where retirement may work best.  
5. Save your best plan in Phase 5 and export a report.
""")

    with tabs[1]:
        st.subheader("Plain-English Retirement Glossary")
        glossary = pd.DataFrame([
            {"Term": "4% Rule", "Plain-English meaning": "A rough guideline that says withdrawing around 4% of a retirement portfolio in the first year may support a long retirement, but it is not a guarantee."},
            {"Term": "Two-Bucket Strategy", "Plain-English meaning": "Keeping near-term spending money in safer assets and long-term money in growth assets to reduce stress during market downturns."},
            {"Term": "Roth Conversion", "Plain-English meaning": "Moving money from a traditional retirement account to a Roth account and paying tax now to potentially reduce future taxes."},
            {"Term": "RMD", "Plain-English meaning": "Required Minimum Distribution. The amount the IRS requires you to withdraw from certain retirement accounts later in life."},
            {"Term": "Rule of 55", "Plain-English meaning": "A rule that may allow penalty-free withdrawals from a current employer's 401(k) if you leave that employer in or after the year you turn 55."},
            {"Term": "Sequence Risk", "Plain-English meaning": "The risk that poor market returns early in retirement hurt your portfolio more because you are withdrawing while markets are down."},
            {"Term": "Taxable Account", "Plain-English meaning": "A brokerage, savings, or investment account that is not tax-sheltered like an IRA or 401(k)."},
            {"Term": "Traditional IRA/401(k)", "Plain-English meaning": "Retirement money that is usually taxed when withdrawn."},
            {"Term": "Roth IRA/401(k)", "Plain-English meaning": "Retirement money that may be tax-free when withdrawn if rules are met."},
            {"Term": "ACA Bridge", "Plain-English meaning": "The period before Medicare where early retirees may need marketplace health insurance and may care about taxable income levels."},
        ])
        st.dataframe(glossary, use_container_width=True, hide_index=True)
        if search:
            st.info(f"Search noted: '{search}'. Future version can filter these resources automatically.")

    with tabs[2]:
        st.subheader("Retirement Rules & Concepts")
        with st.expander("Rule of 55", expanded=True):
            st.write("The Rule of 55 may help some people who leave an employer in or after the year they turn 55 access that employer's 401(k) without the usual 10% early withdrawal penalty. It does not automatically apply to all accounts, old IRAs, or every plan. Users should verify plan rules before relying on it.")
        with st.expander("4% Rule"):
            st.write("The 4% rule is a starting point, not a promise. It does not fully account for taxes, healthcare costs, spending changes, bad early market returns, or personal goals. Use it as a benchmark, then test scenarios in Phase 2.")
        with st.expander("Social Security Timing"):
            st.write("Claiming earlier gives income sooner but usually lowers the monthly benefit. Waiting may increase the monthly benefit, but the best choice depends on health, work plans, spouse benefits, taxes, and how long the money needs to last.")
        with st.expander("RMD Planning"):
            st.write("RMDs can force taxable withdrawals later in retirement. If a user has a large traditional 401(k)/IRA balance, Phase 3 can help show whether Roth conversions or earlier withdrawals may reduce future pressure.")

    with tabs[3]:
        st.subheader("Taxes & Withdrawal Planning")
        tax_table = pd.DataFrame([
            {"Topic": "Cash / Bucket 1", "Why it matters": "Can cover near-term spending and reduce the need to sell growth assets in a down market."},
            {"Topic": "Taxable brokerage", "Why it matters": "May offer flexibility; taxes depend on gains, losses, dividends, and holding period."},
            {"Topic": "Traditional IRA/401(k)", "Why it matters": "Withdrawals are generally taxable and can affect tax brackets, Medicare premiums, and ACA planning."},
            {"Topic": "Roth IRA/401(k)", "Why it matters": "Often valuable to preserve because qualified withdrawals may be tax-free and can provide flexibility later."},
            {"Topic": "HSA", "Why it matters": "Can be very tax-efficient for qualified medical expenses if the user has one."},
        ])
        st.dataframe(tax_table, use_container_width=True, hide_index=True)

        with st.expander("Common withdrawal-order idea"):
            st.write("A common approach is to use cash and taxable assets strategically, manage traditional withdrawals to avoid unnecessary tax spikes, consider Roth conversions during lower-income years, and preserve Roth/HSA assets when possible. The right order depends heavily on age, tax bracket, healthcare, account balances, and spouse situation.")
        with st.expander("Roth conversion reminder"):
            st.write("A Roth conversion can be useful in low-income years, but it creates taxable income in the year of conversion. That can affect tax brackets, ACA subsidies, Medicare IRMAA, and other planning items.")

    with tabs[4]:
        st.subheader("Healthcare & Medicare Bridge")
        st.write("Healthcare is one of the biggest early-retirement planning gaps, especially for people retiring before Medicare eligibility.")
        healthcare_rows = pd.DataFrame([
            {"Age range": "Before 65", "Planning issue": "Need health insurance before Medicare; marketplace/ACA costs may depend on income."},
            {"Age range": "Age 65+", "Planning issue": "Medicare begins for most people, but premiums, supplements, prescriptions, dental, vision, and long-term care still matter."},
            {"Age range": "High income later", "Planning issue": "Higher retirement income may increase Medicare-related costs through IRMAA."},
            {"Age range": "Long-term care", "Planning issue": "Not the same as normal healthcare. May require separate planning, insurance, or self-funding."},
        ])
        st.dataframe(healthcare_rows, use_container_width=True, hide_index=True)
        st.warning("Healthcare assumptions can change quickly by state, age, income, employer coverage, and law. Treat app numbers as estimates.")

    with tabs[5]:
        st.subheader("Lifestyle & Best Places to Retire")
        st.write("Phase 4 is where users compare retirement life, not just money.")
        lifestyle_rows = pd.DataFrame([
            {"Factor": "Taxes", "Why it matters": "State income tax, retirement income treatment, property tax, and sales tax can affect annual spending."},
            {"Factor": "Healthcare access", "Why it matters": "Hospitals, specialists, Medicare networks, and emergency care become more important with age."},
            {"Factor": "Housing/insurance", "Why it matters": "Home prices, rent, HOA fees, property insurance, flood/wind/fire risk can change affordability."},
            {"Factor": "Climate", "Why it matters": "Warm winters may help quality of life, but heat, humidity, hurricanes, wildfire, and water risk matter."},
            {"Factor": "Recreation", "Why it matters": "Golf, beaches, lakes, trails, restaurants, and community activities affect happiness and engagement."},
            {"Factor": "Family proximity", "Why it matters": "Being near children, parents, grandkids, or friends can outweigh pure tax savings."},
        ])
        st.dataframe(lifestyle_rows, use_container_width=True, hide_index=True)

    with tabs[6]:
        st.subheader("Retirement Checklists")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 2–5 Years Before Retirement")
            st.checkbox("Estimate true monthly retirement spending", key="res_check_1")
            st.checkbox("Review Social Security claiming options", key="res_check_2")
            st.checkbox("Build or review Bucket 1 cash/safe assets", key="res_check_3")
            st.checkbox("Estimate healthcare bridge costs", key="res_check_4")
            st.checkbox("Review Roth conversion window", key="res_check_5")
        with col2:
            st.markdown("#### 0–12 Months Before Retirement")
            st.checkbox("Confirm insurance coverage", key="res_check_6")
            st.checkbox("Confirm withdrawal order", key="res_check_7")
            st.checkbox("Update estate documents", key="res_check_8")
            st.checkbox("Create first-year retirement budget", key="res_check_9")
            st.checkbox("Review plan with tax/financial professional", key="res_check_10")

        st.markdown("### Questions to ask a professional")
        st.markdown("""
- Am I eligible for the Rule of 55 with my current employer plan?  
- Should I use Roth conversions before RMD age?  
- How will my Social Security be taxed?  
- What withdrawal order makes sense for my account mix?  
- What healthcare strategy should I use before Medicare?  
- How would my plan change if one spouse passes first?  
""")

def placeholder(title):
    st.title(title)
    st.info("This phase is coming next. The goal is to build one stable phase at a time.")

if nav == "Dashboard":
    show_dashboard()
elif nav == "Phase 1 — Foundation":
    show_phase1()
elif nav == "Phase 2 — Retirement Lab":
    show_phase2()
elif nav == "Phase 3 — Income & Tax":
    show_phase3()
elif nav == "Phase 4 — Lifestyle":
    show_phase4()
elif nav == "Phase 5 — My Plans":
    show_phase5()
elif nav == "Reports":
    show_reports()
elif nav == "AI Coach":
    show_ai_coach()
elif nav == "Resources":
    show_resources()
else:
    placeholder("Resources")
