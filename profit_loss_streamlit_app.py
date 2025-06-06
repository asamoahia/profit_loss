# %% streamlit_app.py
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px
from io import BytesIO
from fpdf import FPDF
import tempfile
import json
import os

# Place this at the top of your script, after your imports
if "reset_triggered" not in st.session_state:
    st.session_state.reset_triggered = False

# Load and Save Session Values
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

# === Streamlit Page Setup ===
st.set_page_config(page_title="Profit & Loss - Full Year", layout="wide")
st.title("📊 Full-Year Profit & Loss Statement")
st.caption("Track your business performance month-by-month")

# === Business Selection ===
available_businesses = ["Reclam Inc.", "Distinct Ent.", "Riverside Worship Ministries"]
business_map = {b.replace(" ", "_").lower(): b for b in available_businesses}

# Step 1: Get the business from URL query parameters
query_params = st.query_params
query_business_key = query_params.get("business", [None])[0] if "business" in query_params else None
selected_from_query = business_map.get(query_business_key, available_businesses[0])

# Step 2: Dropdown for user selection (uses query or default)
selected_business = st.sidebar.selectbox("Select Your Business", available_businesses, index=available_businesses.index(selected_from_query))

# Step 3: Rerun if business changed
if "selected_business" not in st.session_state or st.session_state.selected_business != selected_business:
    st.session_state.clear()
    st.session_state.selected_business = selected_business
    st.rerun()

# Step 4: Update URL with current selection
st.query_params["business"] = selected_business.replace(" ", "_").lower()

# Step 5: Store selected business in session
st.session_state["business_name"] = selected_business

# Step 6: Use selected business for data file
business_id = selected_business.replace(" ", "_").lower()
DATA_FILE = f"stored_values_{business_id}.json"

# Load stored values (if available)
load_session_data()

if st.session_state.reset_triggered:
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.clear()
    st.session_state.reset_triggered = False
    st.rerun()

# === Business-specific logo handling ===
business_id = selected_business.replace(" ", "_").lower()
LOGO_FILE = f"logo_{business_id}.png"

# Load logo from file if not already in session
if f"logo_{business_id}" not in st.session_state:
    if os.path.exists(LOGO_FILE):
        with open(LOGO_FILE, "rb") as f:
            st.session_state[f"logo_{business_id}"] = f.read()
    else:
        st.session_state[f"logo_{business_id}"] = None

# Upload a new logo
uploaded_logo = st.file_uploader("Upload your business logo (PNG or JPG)", type=["png", "jpg", "jpeg"])
if uploaded_logo:
    logo_bytes = uploaded_logo.read()
    st.session_state[f"logo_{business_id}"] = logo_bytes
    with open(LOGO_FILE, "wb") as f:
        f.write(logo_bytes)

# Display logo if available
if st.session_state[f"logo_{business_id}"]:
    st.image(st.session_state[f"logo_{business_id}"], caption=f"{selected_business} Logo", use_column_width=False)

# === Constants ===
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
target_length = 12

# === Sidebar Filters ===
month_filter = st.sidebar.selectbox("Select Month", ["All"] + months)
multi_months_filter = st.sidebar.multiselect("Select Multiple Months for Comparison", months)

tax_rate = st.sidebar.number_input("Tax Rate (%)", min_value=0.0, max_value=100.0, value=10.0)
growth_rate = st.sidebar.number_input("Expected Growth Rate (%)", min_value=0.0, max_value=100.0, value=5.0)

if st.sidebar.button("Reset All Data"):
    st.session_state.reset_triggered = True
    st.rerun()  # Rerun immediately after setting the flag

if st.session_state.reset_triggered:
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.clear()
    st.session_state.reset_triggered = False
    st.rerun()  # Trigger one final rerun with everything cleared

# === Business Info ===
col1, col2 = st.columns(2)
with col1:
    business_name = st.text_input("Business Name", selected_business)
with col2:
    report_year = st.text_input("Year", "2025")

# Monthly Input Helper Function
def monthly_inputs(label, default=0.0):
    st.markdown(f"**{label}**")
    input_values = []

    for i, month in enumerate(months):
        key = f"{label}_{i}"

        # Initialize session state if not already set
        if key not in st.session_state:
            st.session_state[key] = default

        # Only pass 'value' during widget creation if the session state just got initialized
        input_value = st.number_input(
            f"{label} - {month}",
            min_value=0.0,
            step=0.01,
            key=key
        )

        input_values.append(input_value)

    return input_values

# === COLUMNS SECTION START ===
col_rev, col_exp, col_res = st.columns(3)

# --- Revenue and Targets ---
with col_rev:
    st.subheader("💰 Revenue & Targets (Monthly)")
    revenue = monthly_inputs("Revenue")
    target_revenue = monthly_inputs("Target Revenue")

# --- Expenses Breakdown ---
with col_exp:
    st.subheader("🧾 Expenses (Monthly)")

    marketing = monthly_inputs("Marketing")
    salaries = monthly_inputs("Salaries")
    utilities = monthly_inputs("Utilities")
    rent = monthly_inputs("Rent")
    other_expenses = monthly_inputs("Other Expenses")

    # Custom Expenses
    st.markdown("**Add Custom Expense Categories**")
    custom_categories_input = st.text_input("Comma-separated (e.g., Taxes, Insurance)", "Taxes, Insurance")
    custom_expense_categories = [c.strip() for c in custom_categories_input.split(',') if c.strip()]

    custom_expenses_data = {}
    for cat in custom_expense_categories:
        custom_expenses_data[cat] = monthly_inputs(cat)

# --- COGS, Projections & Results ---
with col_res:
    st.subheader("⚙️ COGS & Projections (Monthly)")
    cogs = monthly_inputs("COGS")
    target_expenses = monthly_inputs("Target Expenses")

# Capture All Inputs
save_session_data()

# === Calculations ===

# Total Fixed Expenses per Month
fixed_expenses = [sum(x) for x in zip(marketing, salaries, utilities, rent, other_expenses)]

# Total Custom Expenses per Month
custom_totals = [sum(custom_expenses_data[cat][i] for cat in custom_expense_categories) for i in range(12)]

# Total Expenses = Fixed + Custom
total_expenses = [f + c for f, c in zip(fixed_expenses, custom_totals)]

# Gross Profit = Revenue - COGS
gross_profit = [rev - cost for rev, cost in zip(revenue, cogs)]

# Net Profit = Gross - Expenses
net_profit = [gp - exp for gp, exp in zip(gross_profit, total_expenses)]

# Profit Margin (%) = (Net Profit / Revenue) * 100
profit_margin = [(np / rev * 100) if rev != 0 else 0 for np, rev in zip(net_profit, revenue)]

# Taxes
taxes = [np * (tax_rate / 100) for np in net_profit]
net_profit_after_tax = [np - tax for np, tax in zip(net_profit, taxes)]

# Projections
projected_revenue = [rev * (1 + growth_rate / 100) for rev in revenue]
projected_expenses = [exp * (1 + growth_rate / 100) for exp in total_expenses]
projected_net_profit = [r - e for r, e in zip(projected_revenue, projected_expenses)]

# Variance Calculations
revenue_variance = [rev - tgt for rev, tgt in zip(revenue, target_revenue)]
expense_variance = [exp - tgt for exp, tgt in zip(total_expenses, target_expenses)]

# === Final DataFrame Construction ===
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

# Add a total row
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

# Apply month filter
df_filtered = df[df["Month"] == month_filter] if month_filter != "All" else df

# === Display DataFrame ===
st.markdown("### 📋 P&L Summary Table")
st.dataframe(df_filtered.style.format(
    {col: "${:,.2f}" for col in df_filtered.select_dtypes(include=['number']).columns}
), use_container_width=True)

# === Interactive Plotly Charts ===

# Net Profit Trend
st.markdown("### 📈 Monthly Net Profit After Tax vs Projected")
fig = px.line(df_filtered, x="Month", y=["Net Profit After Tax", "Projected Net Profit"],
              title="Net Profit After Tax vs Projected", markers=True)
st.plotly_chart(fig)

# Revenue Variance
st.markdown("### 📊 Revenue Variance")
fig = px.bar(df_filtered, x="Month", y="Revenue Variance", title="Revenue Variance (Actual vs Target)", color="Revenue Variance")
st.plotly_chart(fig)

# Expense Variance
st.markdown("### 📊 Expense Variance")
fig = px.bar(df_filtered, x="Month", y="Expense Variance", title="Expense Variance (Actual vs Target)", color="Expense Variance")
st.plotly_chart(fig)

# Revenue Chart
st.markdown("### 📈 Revenue Over Time")
fig = px.line(df_filtered, x="Month", y="Revenue", title="Revenue Over Time", markers=True)
st.plotly_chart(fig)

# Profit or Loss Chart
st.markdown("### 📈 Profit or Loss Over Time")
fig = px.line(df_filtered, x="Month", y="Net Profit", title="Profit or Loss Over Time", markers=True)
fig.add_scatter(x=df_filtered["Month"], y=[0]*len(df_filtered), mode='lines', name='Break-even', line=dict(dash='dash'))
st.plotly_chart(fig)

# === Excel Download ===
excel_output = BytesIO()
with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name="P&L Summary", index=False)
    workbook = writer.book
    worksheet = writer.sheets["P&L Summary"]

    # Chart Image
    fig, ax = plt.subplots()
    ax.plot(df["Month"], df["Net Profit"], marker='o')
    ax.set_title("Monthly Net Profit")
    chart_img = BytesIO()
    fig.savefig(chart_img, format='png')
    chart_img.seek(0)
    worksheet.insert_image("R2", "net_profit_chart.png", {"image_data": chart_img})

    # Profit Margin Chart
    fig2, ax2 = plt.subplots()
    ax2.plot(df["Month"], df["Profit Margin (%)"], marker='o')
    ax2.set_title("Profit Margin (%) Over Time")
    margin_chart_img = BytesIO()
    fig2.savefig(margin_chart_img, format='png')
    margin_chart_img.seek(0)
    worksheet.insert_image("R20", "profit_margin_chart.png", {"image_data": margin_chart_img})

st.download_button(
    label="📥 Download Excel Report",
    data=excel_output.getvalue(),
    file_name="P&L_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# === PDF Download ===
def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="P&L Summary Report", ln=True, align='C')

    pdf.set_font("Arial", size=8)
    col_width = pdf.w / (len(dataframe.columns) + 1)
    row_height = 6

    # Table Header
    for col in dataframe.columns:
        pdf.cell(col_width, row_height, str(col)[:12], border=1)
    pdf.ln(row_height)

    # Table Rows
    for i in range(len(dataframe)):
        for col in dataframe.columns:
            val = str(dataframe.iloc[i][col])
            pdf.cell(col_width, row_height, val[:12], border=1)
        pdf.ln(row_height)

    # Net Profit Chart
    fig1, ax1 = plt.subplots()
    ax1.plot(df["Month"], df["Net Profit"], marker='o')
    ax1.axhline(0, color='gray', linestyle='--')
    ax1.set_title("Monthly Net Profit")
    chart_path1 = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    plt.tight_layout()
    fig1.savefig(chart_path1)
    pdf.image(chart_path1, x=10, y=None, w=180)

    # Profit Margin Chart
    fig2, ax2 = plt.subplots()
    ax2.plot(df["Month"], df["Profit Margin (%)"], marker='o', color='green')
    ax2.set_title("Profit Margin (%) Over Time")
    chart_path2 = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    plt.tight_layout()
    fig2.savefig(chart_path2)
    pdf.image(chart_path2, x=10, y=None, w=180)

    return pdf.output(dest="S").encode("latin-1")

pdf_data = create_pdf(df)
st.download_button(
    label="📄 Download PDF Report",
    data=pdf_data,
    file_name="P&L_Report.pdf",
    mime="application/pdf"
)
