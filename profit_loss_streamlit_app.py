# streamlit_app.py

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px
from io import BytesIO
from fpdf import FPDF
import tempfile
import json
import os

# === Page Setup ===
st.set_page_config(page_title="Profit & Loss - Full Year", layout="wide")
st.title("📊 Full-Year Profit & Loss Statement")
st.caption("Track your business performance month-by-month")

# === Select Business ===
st.sidebar.markdown("## 🏢 Select or Create Business")

# Load existing businesses
business_list = [
    f.replace("stored_values_", "").replace(".json", "").replace("_", " ").title()
    for f in os.listdir() if f.startswith("stored_values_") and f.endswith(".json")
]

selected_business = st.sidebar.selectbox("Choose a Business", ["Create New..."] + business_list)

if selected_business == "Create New...":
    new_business_name = st.sidebar.text_input("Enter New Business Name")
    if new_business_name:
        selected_business = new_business_name.strip().title()
else:
    selected_business = selected_business.strip().title()

DATA_FILE = f"stored_values_{selected_business.replace(' ', '_').lower()}.json"

# === Session Reset Handling ===
if "reset_triggered" not in st.session_state:
    st.session_state.reset_triggered = False

if st.sidebar.button("Reset All Data"):
    st.session_state.reset_triggered = True
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.clear()
    st.experimental_rerun()

# === Load and Save ===
def save_session_data():
    data = {key: st.session_state[key] for key in st.session_state if isinstance(st.session_state[key], (int, float, str, bool, list))}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_session_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            for key, value in data.items():
                if key not in st.session_state:
                    st.session_state[key] = value

load_session_data()

# === Constants ===
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# === Persistent Logo Upload ===
if "logo" not in st.session_state:
    st.session_state.logo = None

uploaded_logo = st.file_uploader("Upload your business logo (PNG or JPG)", type=["png", "jpg", "jpeg"])
if uploaded_logo:
    st.session_state.logo = uploaded_logo

logo_file = st.session_state.logo

# === Sidebar Filters ===
month_filter = st.sidebar.selectbox("Select Month", ["All"] + months)
multi_months_filter = st.sidebar.multiselect("Select Multiple Months for Comparison", months)

tax_rate = st.sidebar.number_input("Tax Rate (%)", min_value=0.0, max_value=100.0, value=10.0)
growth_rate = st.sidebar.number_input("Expected Growth Rate (%)", min_value=0.0, max_value=100.0, value=5.0)

# === Business Info ===
col1, col2 = st.columns(2)
with col1:
    business_name = st.text_input("Business Name", selected_business)
with col2:
    report_year = st.text_input("Year", "2025")

# === Monthly Input Helper ===
def monthly_inputs(label, default=0.0):
    st.markdown(f"**{label}**")
    input_values = []
    for i, month in enumerate(months):
        key = f"{label}_{i}"
        if key not in st.session_state:
            st.session_state[key] = default
        input_value = st.number_input(f"{label} - {month}", min_value=0.0, value=st.session_state[key], step=0.01, key=key)
        st.session_state[key] = input_value
        input_values.append(input_value)
    return input_values

# === COLUMNS SECTION ===
col_rev, col_exp, col_res = st.columns(3)

with col_rev:
    st.subheader("💰 Revenue & Targets (Monthly)")
    revenue = monthly_inputs("Revenue")
    target_revenue = monthly_inputs("Target Revenue")

with col_exp:
    st.subheader("🧾 Expenses (Monthly)")
    marketing = monthly_inputs("Marketing")
    salaries = monthly_inputs("Salaries")
    utilities = monthly_inputs("Utilities")
    rent = monthly_inputs("Rent")
    other_expenses = monthly_inputs("Other Expenses")

    st.markdown("**Add Custom Expense Categories**")
    custom_categories_input = st.text_input("Comma-separated (e.g., Taxes, Insurance)", "Taxes, Insurance")
    custom_expense_categories = [c.strip() for c in custom_categories_input.split(',') if c.strip()]

    custom_expenses_data = {}
    for cat in custom_expense_categories:
        custom_expenses_data[cat] = monthly_inputs(cat)

with col_res:
    st.subheader("⚙️ COGS & Projections (Monthly)")
    cogs = monthly_inputs("COGS")
    target_expenses = monthly_inputs("Target Expenses")

# === Calculations ===
save_session_data()

fixed_expenses = [sum(x) for x in zip(marketing, salaries, utilities, rent, other_expenses)]
custom_totals = [sum(custom_expenses_data[cat][i] for cat in custom_expense_categories) for i in range(12)]
total_expenses = [f + c for f, c in zip(fixed_expenses, custom_totals)]

gross_profit = [rev - cost for rev, cost in zip(revenue, cogs)]
net_profit = [gp - exp for gp, exp in zip(gross_profit, total_expenses)]
profit_margin = [(np / rev * 100) if rev != 0 else 0 for np, rev in zip(net_profit, revenue)]
taxes = [np * (tax_rate / 100) for np in net_profit]
net_profit_after_tax = [np - tax for np, tax in zip(net_profit, taxes)]

projected_revenue = [rev * (1 + growth_rate / 100) for rev in revenue]
projected_expenses = [exp * (1 + growth_rate / 100) for exp in total_expenses]
projected_net_profit = [r - e for r, e in zip(projected_revenue, projected_expenses)]

revenue_variance = [rev - tgt for rev, tgt in zip(revenue, target_revenue)]
expense_variance = [exp - tgt for exp, tgt in zip(total_expenses, target_expenses)]

# === Final DataFrame ===
df = pd.DataFrame({
    "Month": months,
    "Revenue": revenue,
    "Target Revenue": target_revenue,
    "Revenue Variance": revenue_variance,
    "COGS": cogs,
    "Gross Profit": gross_profit,
    "Total Expenses": total_expenses,
    "Target Expenses": target_expenses,
    "Expense Variance": expense_variance,
    "Net Profit": net_profit,
    "Profit Margin (%)": profit_margin,
    f"Taxes ({tax_rate}%)": taxes,
    "Net Profit After Tax": net_profit_after_tax,
    "Projected Revenue": projected_revenue,
    "Projected Expenses": projected_expenses,
    "Projected Net Profit": projected_net_profit
})

if month_filter == "All":
    total_row = {
        "Month": "Total",
        "Revenue": sum(revenue),
        "Target Revenue": sum(target_revenue),
        "Revenue Variance": sum(revenue_variance),
        "COGS": sum(cogs),
        "Gross Profit": sum(gross_profit),
        "Total Expenses": sum(total_expenses),
        "Target Expenses": sum(target_expenses),
        "Expense Variance": sum(expense_variance),
        "Net Profit": sum(net_profit),
        f"Taxes ({tax_rate}%)": sum(taxes),
        "Net Profit After Tax": sum(net_profit_after_tax),
        "Projected Revenue": sum(projected_revenue),
        "Projected Expenses": sum(projected_expenses),
        "Projected Net Profit": sum(projected_net_profit)
    }
    df.loc[len(df)] = total_row

df_filtered = df[df["Month"] == month_filter] if month_filter != "All" else df

# === Display ===
st.markdown("### 📋 P&L Summary Table")
st.dataframe(df_filtered.style.format({col: "${:,.2f}" for col in df_filtered.select_dtypes(include=['number']).columns}), use_container_width=True)

# === Plotly Charts ===
st.markdown("### 📈 Monthly Net Profit After Tax vs Projected")
st.plotly_chart(px.line(df_filtered, x="Month", y=["Net Profit After Tax", "Projected Net Profit"], markers=True))

st.markdown("### 📊 Revenue Variance")
st.plotly_chart(px.bar(df_filtered, x="Month", y="Revenue Variance", color="Revenue Variance"))

st.markdown("### 📊 Expense Variance")
st.plotly_chart(px.bar(df_filtered, x="Month", y="Expense Variance", color="Expense Variance"))

st.markdown("### 📈 Revenue Over Time")
st.plotly_chart(px.line(df_filtered, x="Month", y="Revenue", markers=True))

st.markdown("### 📈 Profit or Loss Over Time")
fig = px.line(df_filtered, x="Month", y="Net Profit", markers=True)
fig.add_scatter(x=df_filtered["Month"], y=[0]*len(df_filtered), mode='lines', name='Break-even', line=dict(dash='dash'))
st.plotly_chart(fig)

# === Excel Export ===
excel_output = BytesIO()
with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name="P&L Summary", index=False)

st.download_button("📥 Download Excel Report", data=excel_output.getvalue(), file_name="P&L_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# === PDF Export ===
def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="P&L Summary Report", ln=True, align='C')
    pdf.set_font("Arial", size=8)
    col_width = pdf.w / (len(dataframe.columns) + 1)
    row_height = 6

    for col in dataframe.columns:
        pdf.cell(col_width, row_height, str(col)[:12], border=1)
    pdf.ln(row_height)

    for i in range(len(dataframe)):
        for col in dataframe.columns:
            val = str(dataframe.iloc[i][col])
            pdf.cell(col_width, row_height, val[:12], border=1)
        pdf.ln(row_height)

    return pdf.output(dest="S").encode("latin-1")

pdf_data = create_pdf(df)
st.download_button("📄 Download PDF Report", data=pdf_data, file_name="P&L_Report.pdf", mime="application/pdf")
