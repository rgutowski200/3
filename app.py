import math
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Retirement Blueprint 101",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
        :root {
            --navy: #071b3a;
            --navy-2: #09244c;
            --blue: #1d63ed;
            --green: #159957;
            --red: #ef5753;
            --soft-bg: #f4f7fb;
            --card-border: #dfe6f0;
            --text: #0b1533;
            --muted: #6b7280;
        }

        .stApp { background: var(--soft-bg); }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1500px; }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #061a38 0%, #031326 100%);
            color: white;
        }
        [data-testid="stSidebar"] * { color: white; }
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] select,
        [data-testid="stSidebar"] [data-baseweb="input"] input {
            color: #111827 !important;
            -webkit-text-fill-color: #111827 !important;
            background: white !important;
        }
        [data-testid="stSidebar"] label { color: white !important; }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 18px 18px;
            box-shadow: 0 10px 30px rgba(2, 20, 50, 0.04);
        }

        .rb-card {
            background: white;
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 22px;
            box-shadow: 0 10px 30px rgba(2, 20, 50, 0.04);
            min-height: 175px;
        }
        .rb-card h3 { margin: 0 0 8px 0; font-size: 17px; color: var(--text); }
        .rb-card .big { font-size: 38px; font-weight: 800; color: var(--text); line-height: 1.1; }
        .rb-card .green { color: var(--green); font-weight: 700; }
        .rb-card .muted { color: var(--muted); font-size: 14px; }
        .rb-card a, .rb-link { color: #075eea; font-weight: 700; text-decoration: none; }

        .rb-panel {
            background: white;
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(2, 20, 50, 0.04);
            margin-bottom: 18px;
        }
        .rb-title { font-size: 42px; font-weight: 850; color: var(--text); margin-bottom: 4px; }
        .rb-subtitle { color: var(--muted); font-size: 16px; margin-bottom: 24px; }
        .rb-logo { font-size: 24px; font-weight: 900; line-height: 1.0; margin: 22px 0 28px; }
        .rb-logo small { color: #72d17e; }
        .rb-nav-caption { margin-top: 28px; color: #93a4bb !important; font-size: 12px; letter-spacing: .08em; }
        .rb-upgrade {
            background: rgba(255,255,255,.08);
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 14px;
            padding: 16px;
            margin-top: 28px;
        }
        .rb-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 999px;
            font-weight: 800;
            font-size: 12px;
            background: #e6f7ed;
            color: #137a42;
        }
        .rb-step {
            display: flex;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #edf1f7;
        }
        .rb-num {
            width: 26px; height: 26px; border-radius: 50%;
            background: #eef4ff; color: #0d4db8;
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; flex: 0 0 26px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Helpers
# -----------------------------
def dollars(value: float) -> str:
    return f"${value:,.0f}"


def clamp(value, low, high):
    return max(low, min(high, value))


def projection(age, retire_age, plan_to_age, portfolio, contribution, spend, ss_income, return_rate, inflation):
    years = list(range(int(age), int(plan_to_age) + 1))
    balance = float(portfolio)
    rows = []
    for yr_age in years:
        employment = contribution if yr_age < retire_age else 0
        social_security = ss_income if yr_age >= max(retire_age, 62) else 0
        inflated_spend = spend * ((1 + inflation) ** max(0, yr_age - retire_age)) if yr_age >= retire_age else 0
        withdrawal = max(0, inflated_spend - social_security) if yr_age >= retire_age else 0
        balance = max(0, balance * (1 + return_rate) + employment - withdrawal)
        rows.append(
            {
                "Age": yr_age,
                "Balance": balance,
                "Contribution": employment,
                "Withdrawal": withdrawal,
                "Social Security": social_security,
                "Healthcare": 12000 if retire_age <= yr_age < 65 else 0,
            }
        )
    return pd.DataFrame(rows)


def readiness_score(portfolio, spend, age, retire_age, ss_income):
    years_to_retire = max(0, retire_age - age)
    target = max(1, (spend - ss_income) * 25)
    funded = portfolio / target
    time_bonus = min(15, years_to_retire * 2)
    score = clamp(int(funded * 75 + time_bonus), 0, 100)
    return score


def dashboard_chart(df, age, retire_age):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Age"], y=df["Contribution"] / 12, mode="lines", name="Employment Income", fill="tozeroy"))
    fig.add_trace(go.Scatter(x=df["Age"], y=df["Withdrawal"] / 12, mode="lines", name="Portfolio Withdrawals", fill="tozeroy"))
    fig.add_trace(go.Scatter(x=df["Age"], y=df["Social Security"] / 12, mode="lines", name="Social Security", fill="tozeroy"))
    fig.add_trace(go.Scatter(x=df["Age"], y=df["Healthcare"] / 12, mode="lines", name="Healthcare Costs", line=dict(dash="dash")))
    fig.add_vline(x=retire_age, line_dash="dot", line_color="#159957")
    fig.add_vline(x=62, line_dash="dot", line_color="#7657e8")
    fig.add_vline(x=65, line_dash="dot", line_color="#ef5753")
    fig.add_annotation(x=retire_age, y=0, text=f"{retire_age}<br>Retire", showarrow=False, yshift=-34, bgcolor="white", bordercolor="#159957")
    fig.add_annotation(x=62, y=0, text="62<br>Social Security", showarrow=False, yshift=-34, bgcolor="white", bordercolor="#7657e8")
    fig.add_annotation(x=65, y=0, text="65<br>Medicare", showarrow=False, yshift=-34, bgcolor="white", bordercolor="#ef5753")
    fig.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis_title="Monthly cash flow",
        xaxis_title="Age",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def donut_chart(values, labels):
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.58)])
    fig.update_layout(height=230, margin=dict(l=0, r=0, t=0, b=0), showlegend=True)
    return fig


def score_gauge(score):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 34}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#159957"},
                "steps": [
                    {"range": [0, 50], "color": "#fde2e2"},
                    {"range": [50, 75], "color": "#fff0bf"},
                    {"range": [75, 100], "color": "#d9f5e5"},
                ],
            },
        )
    )
    fig.update_layout(height=210, margin=dict(l=0, r=0, t=0, b=0))
    return fig


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown('<div class="rb-logo">📈 RETIREMENT<br>BLUEPRINT <small>101</small></div>', unsafe_allow_html=True)

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
        label_visibility="collapsed",
    )

    st.markdown('<div class="rb-upgrade"><b>Free demo mode</b><br><br>Dashboard is open. Advanced phases are shown as preview screens in this foundation build.</div>', unsafe_allow_html=True)
    st.divider()

    plan_name = st.text_input("Plan name", value="Base Plan", help="Name your retirement plan or scenario.")
    age = st.number_input("Your age", min_value=18, max_value=90, value=55, help="Your current age today.")
    retire_age = st.slider("Target retirement age", 50, 75, 58, help="The age you want to retire.")
    portfolio = st.number_input("Current retirement savings", min_value=0, value=850000, step=10000)
    spend_monthly = st.number_input("Estimated monthly spending", min_value=0, value=10000, step=500)
    ss_income = st.number_input("Estimated annual Social Security", min_value=0, value=24000, step=1000)
    contribution = st.number_input("Annual contributions until retirement", min_value=0, value=100000, step=5000)
    return_rate = st.slider("Expected growth return", 0.0, 12.0, 7.0, step=0.25) / 100


# -----------------------------
# Core values
# -----------------------------
plan_to_age = 90
annual_spend = spend_monthly * 12
score = readiness_score(portfolio, annual_spend, age, retire_age, ss_income)
confidence = "High" if score >= 75 else "Moderate" if score >= 55 else "Low"
projected_income = max(0, ss_income / 12 + (portfolio * 0.04 / 12))
income_coverage = 0 if spend_monthly == 0 else projected_income / spend_monthly
projection_df = projection(age, retire_age, plan_to_age, portfolio, contribution, annual_spend, ss_income, return_rate, 0.03)


# -----------------------------
# Pages
# -----------------------------
if page == "Dashboard":
    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.markdown('<div class="rb-title">Good morning, John!</div>', unsafe_allow_html=True)
        st.markdown('<div class="rb-subtitle">Here’s your retirement readiness overview.</div>', unsafe_allow_html=True)
    with top_r:
        st.button("🔗 Share Plan", use_container_width=True)
        st.caption(f"Last updated: {date.today().strftime('%b %d, %Y')}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="rb-card"><h3>Retirement Readiness Score</h3>', unsafe_allow_html=True)
        st.plotly_chart(score_gauge(score), use_container_width=True)
        st.markdown(f'<span class="rb-badge">{confidence}</span><p class="muted">Your plan is based on current savings, spending, Social Security, and retirement age.</p><span class="rb-link">See score details →</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="rb-card"><h3>Projected Retirement Age</h3><div class="big">{retire_age}</div><p class="green">Optimal Range: {max(50, retire_age-1)} – {retire_age+5}</p><p class="muted">Goals: Travel, family, comfort, flexibility.</p><br><span class="rb-link">Update Goals →</span></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="rb-card"><h3>Monthly Retirement Income</h3><div class="big">{dollars(projected_income)}</div><p class="green">{income_coverage:.0%} of target spending</p><p class="muted">Includes Social Security and estimated portfolio income.</p><br><span class="rb-link">View Income Breakdown →</span></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="rb-card"><h3>Confidence Level</h3><div class="big" style="color:#159957;">{confidence}</div><p class="muted">Your plan is compared against market, inflation, healthcare, and longevity pressure points.</p><br><span class="rb-link">Run Stress Test →</span></div>', unsafe_allow_html=True)

    main_col, side_col = st.columns([3.4, 1.1])
    with main_col:
        st.markdown('<div class="rb-panel"><h3>Your Retirement Timeline</h3>', unsafe_allow_html=True)
        st.plotly_chart(dashboard_chart(projection_df, age, retire_age), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        a, b, c = st.columns(3)
        with a:
            bridge_years = max(0, 65 - retire_age)
            st.markdown(f'<div class="rb-panel"><h3>Bridge Strategy Summary ({retire_age}–65)</h3><p class="muted">Your plan to bridge the gap to Medicare.</p><hr><b>Healthcare bridge:</b> {dollars(bridge_years * 12000)}<br><b>Rule of 55 withdrawals:</b> {dollars(max(0, annual_spend - ss_income))}<br><b>Cash buffer target:</b> {dollars(annual_spend * 2)}</div>', unsafe_allow_html=True)
        with b:
            values = [max(1, portfolio * 0.04 / 12), max(1, ss_income / 12), max(1, 500), max(1, 300)]
            st.markdown('<div class="rb-panel"><h3>Income Sources at Retirement</h3>', unsafe_allow_html=True)
            st.plotly_chart(donut_chart(values, ["Portfolio", "Social Security", "Other", "Cash"]), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c:
            st.markdown('<div class="rb-panel"><h3>Stress Test Results</h3><p class="muted">Your plan’s resilience.</p><hr><b>Market downturn:</b> Needs Review<br><b>High inflation:</b> Needs Review<br><b>Longer life:</b> On Track<br><br><span class="rb-link">View Full Stress Test →</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="rb-panel"><h3>Compare Retirement Ages</h3><p class="muted">See how different retirement ages impact your plan.</p></div>', unsafe_allow_html=True)
        cols = st.columns(5)
        for i, ra in enumerate([58, 62, 65, 67]):
            with cols[i]:
                st.button(f"Retire at {ra}", use_container_width=True)
        with cols[4]:
            st.button("View Comparison →", use_container_width=True)

    with side_col:
        st.markdown('<div class="rb-panel"><h3>Your Next Steps</h3>', unsafe_allow_html=True)
        steps = [
            ("Review your Bridge Strategy", "Optimize income from retirement to Medicare"),
            ("Run Roth Conversion Scenario", "See if conversions can lower future taxes"),
            ("Check ACA Subsidy Impact", "Lower income could save on healthcare"),
            ("Update Expenses", "Last updated from sidebar estimate"),
        ]
        for i, (title, sub) in enumerate(steps, start=1):
            st.markdown(f'<div class="rb-step"><div class="rb-num">{i}</div><div><b>{title}</b><br><span class="muted">{sub}</span></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="rb-panel"><h3>Market Snapshot</h3><p class="muted">Demo values</p><hr>S&P 500 <b style="float:right; color:#159957;">+1.02%</b><br><br>NASDAQ <b style="float:right; color:#159957;">+1.37%</b><br><br>10-YR Treasury <b style="float:right;">4.46%</b></div>', unsafe_allow_html=True)
        st.markdown('<div class="rb-panel"><h3>Quick Links</h3><hr>📘 Knowledge Hub<br><br>🧮 Retirement Calculators<br><br>📚 Glossary<br><br>👥 Community <span class="muted">Coming Soon</span></div>', unsafe_allow_html=True)

elif page == "Phase 1 — Foundation":
    st.header("Phase 1 — Foundation")
    st.caption("Build the starting point for the retirement plan. This phase will collect household basics, income, spending, Social Security, spouse details, assets, and debt.")
    st.info("Next build step: we add saveable Phase 1 input tabs after the dashboard is stable.")

elif page == "Phase 4 — Lifestyle":
    st.header("Phase 4 — Lifestyle")
    st.caption("Best places to retire, state comparisons, lifestyle preferences, snowbird planning, and personalized location recommendations will live here.")
    st.info("Next build step: we move the full location intelligence engine here after Phase 1 is stable.")

else:
    st.header(page)
    st.caption("Preview page. We are intentionally adding one feature set at a time to keep the build stable.")
    st.info("This section is currently parked until Dashboard → Phase 1 → Phase 4 are stable.")
