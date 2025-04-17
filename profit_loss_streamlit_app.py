import streamlit as st
import os
import json
import pandas as pd
import plotly.express as px
from io import BytesIO
from fpdf import FPDF

# === Get the business name from the URL ===
query_params = st.experimental_get_query_params()
business_name_from_url = query_params.get("business", [None])[0]

if business_name_from_url:
    selected_business = business_name_from_url.replace("_", " ").title()
else:
    selected_business = "Default Business"

DATA_FILE = f"stored_values_{selected_business.replace(' ', '_').lower()}.json"

# === Session Handling and Reset Logic ===
if "reset_triggered" not in st.session_state:
    st.session_state.reset_triggered = False

if st.sidebar.button("Reset All Data"):
    st.session_state.reset_triggered = True
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.clear()
    st.experimental_rerun()

# === Load and Save Session Data ===
def load_session_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            for key, value in data.items():
                if key not in st.session_state:
                    st.session_state[key] = value

def save_session_data():
    data = {key: st.session_state[key] for key in st.session_state if isinstance(st.session_state[key], (int, float, str, bool, list))}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

load_session_data()

# === Business Name Input ===
st.sidebar.markdown("### 🏢 Select or Create Business")
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

# === Load Data based on selected business ===
load_session_data()

# === Inputs and Calculations (similar to previous) ===
# Let's use a helper function to set up monthly inputs and use the session state to retain values

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def monthly_inputs(label, default=0.0):
    input_values = []
    
    for i, month in enumerate(months):
        key = f"{label}_{i}"
        
        # Initialize session state value before widget creation
        if key not in st.session_state:
            st.session_state[key] = default  # Set default value if not set already
        
        # Use the session state value directly as the value, without setting it again as default in the widget
        value = st.session_state[key]  # Get value from session state
        input_value = st.number_input(f"{label} - {month}", min_value=0.0, value=value, step=0.01, key=key)
        
        # Store the new value into session state only if it's updated
        if input_value != value:
            st.session_state[key] = input_value
        
        input_values.append(input_value)
        
    return input_values

# === Display the input fields for business data ===
st.subheader(f"Manage Data for {selected_business}")

# --- Revenue and Expenses Inputs ---
revenue = monthly_inputs("Revenue")
target_revenue = monthly_inputs("Target Revenue")
marketing = monthly_inputs("Marketing")
salaries = monthly_inputs("Salaries")
utilities = monthly_inputs("Utilities")
rent = monthly_inputs("Rent")
other_expenses = monthly_inputs("Other Expenses")

# --- Save Data after inputs ===
save_session_data()

# === Show Calculations (e.g., Net Profit, Revenue Over Time) ===
# Example: Calculate Net Profit (Revenue - Expenses)
total_expenses = [sum(x) for x in zip(marketing, salaries, utilities, rent, other_expenses)]
net_profit = [rev - exp for rev, exp in zip(revenue, total_expenses)]

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
