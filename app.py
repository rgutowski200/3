import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Retirement Blueprint 101", layout="wide")

# ----------------------------
# App Styling
# ----------------------------
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #061A3A 0%, #081F45 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    .metric-card {
        background: #ffffff;
        border: 1px solid #e6eaf0;
        border-radius: 18px;
        padding: 22px;
        min-height: 155px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
    }
    .small-muted {
        color: #64748b;
        font-size: 0.92rem;
    }
    .good {
        color: #159947;
        font-weight: 700;
    }
    .blue-banner {
        background: #eaf4ff;
        border: 1px solid #cfe8ff;
        border-radius: 14px;
        padding: 16px 18px;
        color: #0f4c81;
    }
    .locked-card {
        border: 1px dashed #cbd5e1;
        border-radius: 16px;
        padding: 18px;
        background: #f8fafc;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Session State Defaults
# ----------------------------
defaults = {
    "nav_page": "Dashboard",
    "premium_demo": True,
    "plan_name": "Base Plan",

    "phase1_name": "John",
    "phase1_age": 55,
    "phase1_retire_age": 58,
    "phase1_plan_age": 90,
    "phase1_depth": "Simple",

    "phase1_income": 140000,
    "phase1_other_income": 0,
    "phase1_monthly_spending": 10400,
    "phase1_use_detailed_budget": False,

    "budget_housing": 3000,
    "budget_food": 1200,
    "budget_healthcare": 1000,
    "budget_travel": 1500,
    "budget_transportation": 900,
    "budget_insurance": 700,
    "budget_entertainment": 900,
    "budget_other": 1200,

    "phase1_ss_age": 62,
    "phase1_social_security": 24000,
    "phase1_portfolio": 850000,
    "phase1_home_equity": 300000,
    "phase1_debt": 0,

    "phase1_spouse_enabled": False,
    "phase1_spouse_age": 53,
    "phase1_spouse_income": 0,
    "phase1_spouse_ss": 24000,

    "phase1_healthcare_bridge": 12000,
    "phase1_bucket_years": 3.0,
    "phase1_inflation": 3.0,
    "phase1_growth_return": 7.0,

    "phase1_roth_conversion": 0,
    "phase1_tax_rate": 18.0,
    "phase1_aca_magi_target": 60000,
    "phase1_bad_market": -20.0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ----------------------------
# Helper Functions
# ----------------------------
def money(value):
    return f"${value:,.0f}"

def pct(value):
    return f"{value:.0f}%"

def annual_spending():
    if st.session_state.phase1_use_detailed_budget:
        total = (
            st.session_state.budget_housing
            + st.session_state.budget_food
            + st.session_state.budget_healthcare
            + st.session_state.budget_travel
            + st.session_state.budget_transportation
            + st.session_state.budget_insurance
            + st.session_state.budget_entertainment
            + st.session_state.budget_other
        )
        return total * 12
    return st.session_state.phase1_monthly_spending * 12

def guaranteed_income():
    total = st.session_state.phase1_social_security + st.session_state.phase1_other_income
    if st.session_state.phase1_spouse_enabled:
        total += st.session_state.phase1_spouse_ss + st.session_state.phase1_spouse_income
    return total

def readiness_score():
    spending = max(annual_spending(), 1)
    income = guaranteed_income()
    portfolio_income = st.session_state.phase1_portfolio * 0.04
    coverage = (income + portfolio_income) / spending
    score = int(min(100, max(0, coverage * 82)))
    return score

def confidence_label(score):
    if score >= 75:
        return "High"
    if score >= 55:
        return "Medium"
    return "Needs Review"

def save_phase1():
    saved = {}
    for key in list(st.session_state.keys()):
        if key.startswith("phase1_") or key.startswith("budget_"):
            saved[key] = st.session_state[key]
    st.session_state["saved_phase1"] = saved

def load_phase1():
    saved = st.session_state.get("saved_phase1", {})
    for key, value in saved.items():
        st.session_state[key] = value

def clear_phase1():
    for key, value in defaults.items():
        if key.startswith("phase1_") or key.startswith("budget_"):
            st.session_state[key] = value

# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.markdown("## 📈 RETIREMENT\n## BLUEPRINT 101")
    st.divider()

    page = st.radio(
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
        key="nav_page",
    )

    st.divider()

    st.toggle("Premium demo unlocked", key="premium_demo")

    if st.session_state.premium_demo:
        st.success("Premium unlocked")
    else:
        st.info("Free dashboard mode")

    st.markdown("### Quick Assumptions")
    st.text_input("Plan name", key="plan_name")
    st.number_input("Your age", min_value=45, max_value=90, key="sidebar_age", value=st.session_state.phase1_age)
    st.slider("Target retirement age", 50, 75, key="sidebar_retire_age", value=st.session_state.phase1_retire_age)
    st.number_input("Estimated monthly spend", min_value=0, step=500, key="sidebar_monthly_spend", value=st.session_state.phase1_monthly_spending)

# ----------------------------
# Dashboard
# ----------------------------
def show_dashboard():
    score = readiness_score()
    confidence = confidence_label(score)
    spending = annual_spending()
    income = guaranteed_income()
    monthly_income_est = (income + st.session_state.phase1_portfolio * 0.04) / 12

    st.markdown(f"# Good morning, {st.session_state.phase1_name}!")
    st.write("Here’s your retirement readiness overview.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <b>Retirement Readiness Score</b>
                <h1>{score}<span style="font-size:1.1rem;">/100</span></h1>
                <div class="good">{'On Track' if score >= 70 else 'Needs Review'}</div>
                <p class="small-muted">Based on income coverage, portfolio strength, spending, and retirement timing.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <b>Projected Retirement Age</b>
                <h1>{st.session_state.phase1_retire_age}</h1>
                <div class="good">Optimal Range: 58–63</div>
                <p class="small-muted">Adjust this in Phase 1 to compare timing.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <b>Monthly Retirement Income</b>
                <h1>{money(monthly_income_est)}</h1>
                <div class="good">{pct(min(100, monthly_income_est / max(spending / 12, 1) * 100))} of target spending</div>
                <p class="small-muted">Includes Social Security, other income, and a simple 4% portfolio estimate.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <b>Confidence Level</b>
                <h1>{confidence}</h1>
                <p class="small-muted">Your plan gets stronger as you add more detail in Phase 1.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Your Retirement Timeline")

    ages = list(range(st.session_state.phase1_age, st.session_state.phase1_plan_age + 1))
    portfolio = []
    bal = st.session_state.phase1_portfolio
    for age in ages:
        if age < st.session_state.phase1_retire_age:
            bal = bal * (1 + st.session_state.phase1_growth_return / 100)
        else:
            withdrawal = max(0, spending - income)
            bal = max(0, bal * (1 + st.session_state.phase1_growth_return / 100) - withdrawal)
        portfolio.append(bal)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ages, y=portfolio, mode="lines", name="Portfolio"))
    fig.add_vline(x=st.session_state.phase1_retire_age, line_dash="dash", annotation_text="Retire")
    fig.add_vline(x=st.session_state.phase1_ss_age, line_dash="dot", annotation_text="Social Security")
    fig.update_layout(height=340, margin=dict(l=20, r=20, t=30, b=20), yaxis_title="Portfolio")
    st.plotly_chart(fig, use_container_width=True)

    l1, l2, l3 = st.columns([1, 1, 1])
    with l1:
        st.markdown("### Next Steps")
        st.write("1. Complete Phase 1 Foundation")
        st.write("2. Run a retirement age comparison")
        st.write("3. Add Social Security and spouse assumptions")
    with l2:
        st.markdown("### Income Sources")
        st.metric("Guaranteed Income", money(income))
        st.metric("Annual Spending", money(spending))
    with l3:
        st.markdown("### Stress Test Snapshot")
        st.success("Market downturn: review in Phase 2")
        st.success("Inflation: review in Phase 3")
        st.success("Longevity: review in Phase 5")

# ----------------------------
# Phase 1
# ----------------------------
def show_phase1():
    st.markdown("# Phase 1 — Financial Foundation")
    st.write("Build the base retirement picture: income, spending, assets, debt, Social Security, and spouse planning.")

    st.markdown(
        """
        <div class="blue-banner">
        Free users can enter basic estimates. Premium users can go deeper with category spending,
        other income sources, spouse planning, and Social Security assumptions.
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs([
        "1. Household",
        "2. Income",
        "3. Spending",
        "4. Social Security",
        "5. Assets & Debt",
        "6. Spouse / Partner",
    ])

    with tabs[0]:
        st.subheader("Household Basics")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("First name", key="phase1_name")
        with c2:
            st.number_input("Current age", min_value=45, max_value=90, key="phase1_age")
        with c3:
            st.slider("Retirement age", 50, 75, key="phase1_retire_age")

        c4, c5 = st.columns(2)
        with c4:
            st.slider("Plan through age", 75, 100, key="phase1_plan_age")
        with c5:
            st.selectbox("Planning depth", ["Simple", "Standard", "Advanced"], key="phase1_depth")

    with tabs[1]:
        st.subheader("Income")
        c1, c2 = st.columns(2)
        with c1:
            st.number_input("Current household income", min_value=0, step=5000, key="phase1_income")
        with c2:
            st.number_input("Other annual income in retirement", min_value=0, step=1000, key="phase1_other_income")

        if st.session_state.phase1_depth in ["Standard", "Advanced"]:
            st.text_area("Describe other income resources", placeholder="Pension, rental income, annuity, part-time work, business income...")

    with tabs[2]:
        st.subheader("Spending")
        st.checkbox("Use detailed monthly budget", key="phase1_use_detailed_budget")

        if not st.session_state.phase1_use_detailed_budget:
            st.number_input("Estimated monthly retirement spending", min_value=0, step=500, key="phase1_monthly_spending")
        else:
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                st.number_input("Housing", min_value=0, step=100, key="budget_housing")
                st.number_input("Food", min_value=0, step=100, key="budget_food")
            with b2:
                st.number_input("Healthcare", min_value=0, step=100, key="budget_healthcare")
                st.number_input("Travel", min_value=0, step=100, key="budget_travel")
            with b3:
                st.number_input("Transportation", min_value=0, step=100, key="budget_transportation")
                st.number_input("Insurance", min_value=0, step=100, key="budget_insurance")
            with b4:
                st.number_input("Entertainment", min_value=0, step=100, key="budget_entertainment")
                st.number_input("Other", min_value=0, step=100, key="budget_other")

    with tabs[3]:
        st.subheader("Social Security")
        c1, c2 = st.columns(2)
        with c1:
            st.slider("Your Social Security start age", 62, 70, key="phase1_ss_age")
        with c2:
            st.number_input("Your annual Social Security", min_value=0, step=1000, key="phase1_social_security")

    with tabs[4]:
        st.subheader("Assets & Debt")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input("Investment portfolio", min_value=0, step=10000, key="phase1_portfolio")
        with c2:
            st.number_input("Home equity", min_value=0, step=10000, key="phase1_home_equity")
        with c3:
            st.number_input("Total debt", min_value=0, step=5000, key="phase1_debt")

        if st.session_state.phase1_depth in ["Standard", "Advanced"]:
            st.markdown("### Standard Planning Assumptions")
            c4, c5, c6 = st.columns(3)
            with c4:
                st.number_input("Annual healthcare bridge cost", min_value=0, step=1000, key="phase1_healthcare_bridge")
            with c5:
                st.number_input("Bucket 1 target years", min_value=1.0, max_value=6.0, step=0.5, key="phase1_bucket_years")
            with c6:
                st.slider("Inflation assumption", 0.0, 8.0, key="phase1_inflation")

        if st.session_state.phase1_depth == "Advanced":
            st.markdown("### Advanced Planning Assumptions")
            a1, a2, a3 = st.columns(3)
            with a1:
                st.number_input("Annual Roth conversion to test", min_value=0, step=5000, key="phase1_roth_conversion")
            with a2:
                st.slider("Estimated tax rate", 0.0, 40.0, key="phase1_tax_rate")
            with a3:
                st.number_input("ACA MAGI target", min_value=0, step=5000, key="phase1_aca_magi_target")
            st.slider("Bad-market stress test return", -50.0, 0.0, key="phase1_bad_market")

    with tabs[5]:
        st.subheader("Spouse / Partner")
        st.checkbox("Include spouse or partner in this plan", key="phase1_spouse_enabled")

        if st.session_state.phase1_spouse_enabled:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.number_input("Spouse age", min_value=45, max_value=90, key="phase1_spouse_age")
            with c2:
                st.number_input("Spouse annual income", min_value=0, step=5000, key="phase1_spouse_income")
            with c3:
                st.number_input("Spouse annual Social Security", min_value=0, step=1000, key="phase1_spouse_ss")
        else:
            st.info("No spouse or partner is included in this scenario.")

    st.divider()
    st.subheader("Foundation Summary")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Annual Spending", money(annual_spending()))
    s2.metric("Guaranteed Income", money(guaranteed_income()))
    s3.metric("Portfolio", money(st.session_state.phase1_portfolio))
    s4.metric("Home Equity", money(st.session_state.phase1_home_equity))

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Save Phase 1 inputs"):
            save_phase1()
            st.success("Phase 1 inputs saved for this session.")
    with c2:
        if st.button("Load saved Phase 1"):
            load_phase1()
            st.success("Saved Phase 1 inputs loaded.")
    with c3:
        if st.button("Clear Phase 1"):
            clear_phase1()
            st.success("Phase 1 inputs cleared.")

# ----------------------------
# Placeholder Pages
# ----------------------------
def locked_or_placeholder(title, desc):
    st.markdown(f"# {title}")
    st.write(desc)
    if not st.session_state.premium_demo:
        st.markdown(
            """
            <div class="locked-card">
                <h3>Premium feature</h3>
                <p>Upgrade to unlock this planning module.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("This module is ready for the next build step.")

# ----------------------------
# Router
# ----------------------------
if page == "Dashboard":
    show_dashboard()
elif page == "Phase 1 — Foundation":
    show_phase1()
elif page == "Phase 2 — Retirement Lab":
    locked_or_placeholder("Phase 2 — Retirement Lab", "Compare retirement ages, withdrawals, bridge strategy, and stress tests.")
elif page == "Phase 3 — Income & Tax":
    locked_or_placeholder("Phase 3 — Income & Tax", "Plan Social Security, taxes, Roth conversions, ACA, and RMDs.")
elif page == "Phase 4 — Lifestyle":
    locked_or_placeholder("Phase 4 — Lifestyle", "Compare best places to retire, lifestyle fit, state taxes, and snowbird options.")
elif page == "Phase 5 — My Plans":
    locked_or_placeholder("Phase 5 — My Plans", "Save scenarios, compare plans, and generate your final retirement blueprint.")
else:
    locked_or_placeholder(page, "This section will be built after the foundation is stable.")
