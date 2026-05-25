import streamlit as st

st.set_page_config(
    page_title="Retirement Blueprint 101",
    layout="wide"
)

# ----------------------------
# SESSION STATE DEFAULTS
# ----------------------------

defaults = {
    "name": "John",
    "age": 55,
    "retire_age": 58,
    "plan_age": 90,
    "income": 140000,
    "monthly_spending": 10400,
    "social_security": 24000,
    "portfolio": 850000,
    "home_equity": 300000,
    "spouse_enabled": False,
    "spouse_age": 53,
    "spouse_ss": 24000,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ----------------------------
# SIDEBAR
# ----------------------------

with st.sidebar:
    st.title("📈 RETIREMENT\nBLUEPRINT 101")

    st.markdown("### Navigation")

    st.radio(
        "Go To",
        [
            "Dashboard",
            "Phase 1 — Foundation",
            "Phase 2 — Retirement Lab",
            "Phase 3 — Income & Tax",
            "Phase 4 — Lifestyle",
            "Phase 5 — My Plans",
            "Reports",
            "AI Coach",
            "Resources"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.markdown("### Quick Assumptions")

    st.text_input(
        "Plan name",
        value="Base Plan"
    )

    st.number_input(
        "Your age",
        min_value=45,
        max_value=90,
        key="age"
    )

    st.slider(
        "Target retirement age",
        50,
        75,
        key="retire_age"
    )

    st.number_input(
        "Estimated monthly spend",
        min_value=0,
        step=500,
        key="monthly_spending"
    )

# ----------------------------
# MAIN PAGE
# ----------------------------

st.title("Phase 1 — Financial Foundation")

st.write(
    "Build the base retirement picture: income, spending, assets, debt, Social Security, and spouse planning."
)

tabs = st.tabs([
    "1. Household",
    "2. Income",
    "3. Spending",
    "4. Social Security",
    "5. Assets & Debt",
    "6. Spouse / Partner"
])

# ----------------------------
# TAB 1
# ----------------------------

with tabs[0]:

    st.subheader("Household Basics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.text_input(
            "First name",
            key="name"
        )

    with col2:
        st.number_input(
            "Current age",
            min_value=45,
            max_value=90,
            key="age"
        )

    with col3:
        st.slider(
            "Retirement age",
            50,
            75,
            key="retire_age"
        )

    st.slider(
        "Plan through age",
        75,
        100,
        key="plan_age"
    )

# ----------------------------
# TAB 2
# ----------------------------

with tabs[1]:

    st.subheader("Income")

    st.number_input(
        "Current household income",
        min_value=0,
        step=5000,
        key="income"
    )

    st.text_area(
        "Other income sources",
        placeholder="Rental income, pension, side business, annuity..."
    )

# ----------------------------
# TAB 3
# ----------------------------

with tabs[2]:

    st.subheader("Spending")

    st.number_input(
        "Estimated monthly retirement spending",
        min_value=0,
        step=500,
        key="monthly_spending"
    )

    st.expander("Detailed monthly budget").write("""
    Future feature:
    - Housing
    - Food
    - Healthcare
    - Travel
    - Entertainment
    - Insurance
    """)

# ----------------------------
# TAB 4
# ----------------------------

with tabs[3]:

    st.subheader("Social Security")

    st.number_input(
        "Your annual Social Security",
        min_value=0,
        step=1000,
        key="social_security"
    )

# ----------------------------
# TAB 5
# ----------------------------

with tabs[4]:

    st.subheader("Assets & Debt")

    col1, col2 = st.columns(2)

    with col1:
        st.number_input(
            "Investment portfolio",
            min_value=0,
            step=10000,
            key="portfolio"
        )

    with col2:
        st.number_input(
            "Home equity",
            min_value=0,
            step=10000,
            key="home_equity"
        )

# ----------------------------
# TAB 6
# ----------------------------

with tabs[5]:

    st.subheader("Spouse / Partner")

    st.checkbox(
        "Include spouse in plan",
        key="spouse_enabled"
    )

    if st.session_state.spouse_enabled:

        col1, col2 = st.columns(2)

        with col1:
            st.number_input(
                "Spouse age",
                min_value=45,
                max_value=90,
                key="spouse_age"
            )

        with col2:
            st.number_input(
                "Spouse annual Social Security",
                min_value=0,
                step=1000,
                key="spouse_ss"
            )

# ----------------------------
# SUMMARY
# ----------------------------

st.divider()

st.subheader("Foundation Summary")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Annual Spending",
    f"${st.session_state.monthly_spending * 12:,.0f}"
)

c2.metric(
    "Guaranteed Income",
    f"${st.session_state.social_security:,.0f}"
)

c3.metric(
    "Portfolio",
    f"${st.session_state.portfolio:,.0f}"
)

c4.metric(
    "Home Equity",
    f"${st.session_state.home_equity:,.0f}"
)

st.success("Inputs are automatically saved during your session.")
