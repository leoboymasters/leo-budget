import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import altair as alt
import traceback

# Page configuration
st.set_page_config(
    page_title="Budget Tracker",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (keeping the existing styles)
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        background-color: #3b82f6;
        color: white;
        font-weight: 500;
    }
    div[data-testid="stForm"] {
        border: none;
        padding: 0;
    }
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #3b82f6;
        color: white;
    }
    .metric-card {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #6b7280;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .income {
        color: #10b981;
    }
    .expense {
        color: #ef4444;
    }
    .stTabs {
        background-color: white;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #e5e7eb;
    }
    .stDataFrame {
        background-color: white;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Google Sheets connection (keeping existing function)
@st.cache_resource
def init_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], 
            scope
        )
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets: {str(e)}")
        return None

def ensure_worksheet_exists():
    try:
        client = init_google_sheets()
        if client is None:
            return False
        spreadsheet = client.open_by_key(st.secrets["spreadsheet_id"])
        try:
            worksheet = spreadsheet.worksheet("Transactions")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Transactions", rows="1000", cols="6")  # Added one more column for spending_type
            headers = ["date", "description", "amount", "category", "type", "spending_type"]
            worksheet.append_row(headers)
        return True
    except Exception as e:
        st.error(f"Error ensuring worksheet exists: {str(e)}")
        return False

def add_transaction(date, description, amount, category, type_, spending_type):
    try:
        if not ensure_worksheet_exists():
            return False
        client = init_google_sheets()
        sheet = client.open_by_key(st.secrets["spreadsheet_id"]).worksheet("Transactions")
        row = [date, description, amount, category, type_, spending_type]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error adding transaction: {str(e)}")
        return False

def load_transactions():
    try:
        client = init_google_sheets()
        if client:
            sheet = client.open_by_key(st.secrets["spreadsheet_id"]).worksheet("Transactions")
            data = sheet.get_all_records()
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading transactions: {str(e)}")
        return pd.DataFrame()

# Sidebar
with st.sidebar:
    st.title("Budget Tracker")
    
    # Initialize session state for transaction type if not exists
    if 'transaction_type' not in st.session_state:
        st.session_state.transaction_type = "Need"
        
    # Updated transaction form
    st.subheader("Add Transaction")
    
    # Transaction type selector outside the form
    transaction_type = st.selectbox(
        "Transaction Type",
        ["Need", "Want", "Savings", "Income"],
        key="transaction_type"
    )
    
    # Define categories based on transaction type
    categories = {
        "Need": ["Rent", "Food", "Utilities", "Transportation", "Healthcare", "Education", "Insurance"],
        "Want": ["Entertainment", "Shopping", "Dining", "Travel", "Hobbies", "Subscriptions", "Gifts"],
        "Savings": ["Emergency Fund", "Investments", "Retirement", "Goals", "Debt Payment"],
        "Income": ["Salary", "Freelance", "Business", "Investments", "Other Income"]
    }
    
    with st.form("transaction_form"):
        description = st.text_input("Description")
        amount = st.number_input("Amount", step=5, value=None)
        
        category = st.selectbox(
            "Category",
            categories.get(transaction_type, ["Other"])
        )
        # Date input at the bottom of the form
        date = st.date_input("Date", datetime.now())
        submitted = st.form_submit_button("Add Transaction")
        
        if submitted and description and amount:
            transaction_type = "income" if transaction_type == "Income" else "expense"
            if add_transaction(
                date.strftime('%Y-%m-%d'),
                description,
                amount,
                category,
                transaction_type,
                st.session_state.transaction_type  # Use the transaction type from session state
            ):
                st.success("Transaction added!")
                st.experimental_rerun()
        # Display budget allocations first
        
    # Add custom CSS for budget cards
    st.markdown("""
        <style>
            .budget-card {
                background-color: white;
                border-radius: 10px;
                padding: 1rem;
                margin-bottom: 1rem;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .budget-title {
                color: #4B5563;
                font-size: 0.875rem;
                margin-bottom: 0.5rem;
            }
            .budget-amount {
                color: #111827;
                font-size: 1.25rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
            }
            .budget-subtitle {
                color: #6B7280;
                font-size: 0.75rem;
                margin-bottom: 0.5rem;
            }
            .progress-container {
                background-color: #E5E7EB;
                border-radius: 9999px;
                height: 8px;
                margin-top: 0.5rem;
            }
            .progress-needs {
                background-color: #3B82F6;
                height: 100%;
                border-radius: 9999px;
                transition: width 0.5s ease;
            }
            .progress-wants {
                background-color: #10B981;
                height: 100%;
                border-radius: 9999px;
                transition: width 0.5s ease;
            }
            .progress-savings {
                background-color: #6366F1;
                height: 100%;
                border-radius: 9999px;
                transition: width 0.5s ease;
            }
            .percent-text {
                color: #6B7280;
                font-size: 0.75rem;
                text-align: right;
                margin-top: 0.25rem;
            }
        </style>
    """, unsafe_allow_html=True)

    if 'df' not in locals():
        df = load_transactions()
    
    if not df.empty and 'spending_type' in df.columns:
        total_income = df[df['type'] == 'income']['amount'].sum()
        
        # Calculate budgets and spending
        needs_spent = abs(df[(df['type'] == 'expense') & (df['spending_type'] == 'Need')]['amount'].sum())
        wants_spent = abs(df[(df['type'] == 'expense') & (df['spending_type'] == 'Want')]['amount'].sum())
        savings_spent = abs(df[(df['type'] == 'expense') & (df['spending_type'] == 'Savings')]['amount'].sum())
        
        needs_budget = total_income * 0.5
        wants_budget = total_income * 0.3
        savings_budget = total_income * 0.2
        
        # Calculate percentages
        needs_percent = min((needs_spent / needs_budget * 100 if needs_budget > 0 else 0), 100)
        wants_percent = min((wants_spent / wants_budget * 100 if wants_budget > 0 else 0), 100)
        savings_percent = min((savings_spent / savings_budget * 100 if savings_budget > 0 else 0), 100)
        
        st.header("Budget Overview")
        
        # Needs Card
        st.markdown(f"""
            <div class="budget-card">
                <div class="budget-title">NEEDS (50%)</div>
                <div class="budget-amount">₱{needs_budget - needs_spent:,.2f}</div>
                <div class="budget-subtitle">remaining of ₱{needs_budget:,.2f}</div>
                <div class="progress-container">
                    <div class="progress-needs" style="width: {needs_percent}%"></div>
                </div>
                <div class="percent-text">{needs_percent:.1f}% used</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Wants Card
        st.markdown(f"""
            <div class="budget-card">
                <div class="budget-title">WANTS (30%)</div>
                <div class="budget-amount">₱{wants_budget - wants_spent:,.2f}</div>
                <div class="budget-subtitle">remaining of ₱{wants_budget:,.2f}</div>
                <div class="progress-container">
                    <div class="progress-wants" style="width: {wants_percent}%"></div>
                </div>
                <div class="percent-text">{wants_percent:.1f}% used</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Savings Card
        st.markdown(f"""
            <div class="budget-card">
                <div class="budget-title">SAVINGS (20%)</div>
                <div class="budget-amount">₱{savings_budget - savings_spent:,.2f}</div>
                <div class="budget-subtitle">remaining of ₱{savings_budget:,.2f}</div>
                <div class="progress-container">
                    <div class="progress-savings" style="width: {savings_percent}%"></div>
                </div>
                <div class="percent-text">{savings_percent:.1f}% used</div>
            </div>
        """, unsafe_allow_html=True)

# Main content
st.title("Dashboard Overview")

# Load and calculate metrics
df = load_transactions()
if not df.empty:
    df['amount'] = pd.to_numeric(df['amount'])
    total_income = df[df['type'] == 'income']['amount'].sum()
    total_expenses = abs(df[df['type'] == 'expense']['amount'].sum())
    balance = total_income - total_expenses

    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-label">Total Balance</div>
                <div class="metric-value">₱%.2f</div>
            </div>
        """ % balance, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-label">Total Income</div>
                <div class="metric-value income">₱%.2f</div>
            </div>
        """ % total_income, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-label">Total Expenses</div>
                <div class="metric-value expense">₱%.2f</div>
            </div>
        """ % total_expenses, unsafe_allow_html=True)

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Transactions", "Analytics", "Budget Planning"])
    
    with tab1:
        st.subheader("Recent Transactions")
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_categories = st.multiselect(
                "Filter by Category",
                options=df['category'].unique(),
                default=df['category'].unique()
            )
        with col2:
            transaction_type = st.multiselect(
                "Filter by Type",
                options=['income', 'expense'],
                default=['income', 'expense']
            )
        with col3:
            # Check if spending_type column exists
            if 'spending_type' in df.columns:
                spending_types = st.multiselect(
                    "Filter by Spending Type",
                    options=df['spending_type'].unique(),
                    default=df['spending_type'].unique()
                )
            else:
                spending_types = ['All']
        
        # Filter and display transactions
        # Create mask based on available columns
        mask = (
            df['category'].isin(selected_categories) & 
            df['type'].isin(transaction_type)
        )
        
        # Add spending_type filter only if the column exists
        if 'spending_type' in df.columns and spending_types != ['All']:
            mask = mask & df['spending_type'].isin(spending_types)
        filtered_df = df[mask].sort_values('date', ascending=False)
        
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )
    
    with tab2:
        st.subheader("Spending Analysis")
        
        # 50/30/20 Budget Analysis
        if total_income > 0:
            st.subheader("50/30/20 Budget Rule Analysis")
            
            # Calculate ideal allocations
            ideal_needs = total_income * 0.5
            ideal_wants = total_income * 0.3
            ideal_savings = total_income * 0.2
            
            # Calculate actual spending with fallback for missing column
            if 'spending_type' in df.columns:
                actual_needs = abs(df[(df['type'] == 'expense') & (df['spending_type'] == 'Need')]['amount'].sum())
                actual_wants = abs(df[(df['type'] == 'expense') & (df['spending_type'] == 'Want')]['amount'].sum())
                actual_savings = abs(df[(df['type'] == 'expense') & (df['spending_type'] == 'Savings')]['amount'].sum())
            else:
                actual_needs = 0
                actual_wants = 0
                actual_savings = 0
            
            # Create comparison data
            budget_comparison = pd.DataFrame({
                'Category': ['Needs', 'Wants', 'Savings'] * 2,
                'Amount': [ideal_needs, ideal_wants, ideal_savings, 
                          actual_needs, actual_wants, actual_savings],
                'Type': ['Ideal', 'Ideal', 'Ideal', 
                        'Actual', 'Actual', 'Actual']
            })
            
            # Create the comparison chart
            chart = alt.Chart(budget_comparison).mark_bar().encode(
                x='Category:N',
                y='Amount:Q',
                color=alt.Color('Type:N', scale=alt.Scale(
                    domain=['Ideal', 'Actual'],
                    range=['#93c5fd', '#3b82f6']
                )),
                column='Type:N'
            ).properties(
                width=200,
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)
            
            # Display percentages
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Needs", f"{(actual_needs/total_income*100):.1f}%", 
                         f"{((actual_needs/total_income*100) - 50):.1f}%")
            with col2:
                st.metric("Wants", f"{(actual_wants/total_income*100):.1f}%", 
                         f"{((actual_wants/total_income*100) - 30):.1f}%")
            with col3:
                st.metric("Savings", f"{(actual_savings/total_income*100):.1f}%", 
                         f"{((actual_savings/total_income*100) - 20):.1f}%")
        
        # Existing monthly trend chart
        monthly_data = df.copy()
        monthly_data['date'] = pd.to_datetime(monthly_data['date'])
        monthly_data['month'] = monthly_data['date'].dt.strftime('%Y-%m')
        
        monthly_summary = monthly_data.groupby(['month', 'type'])['amount'].sum().unstack()
        
        if 'expense' in monthly_summary.columns:
            monthly_summary['expense'] = monthly_summary['expense'].abs()
        
        chart_data = monthly_summary.reset_index()
        
        if not chart_data.empty:
            st.subheader("Monthly Income vs Expenses")
            chart = alt.Chart(chart_data).transform_fold(
                ['income', 'expense'],
                as_=['type', 'amount']
            ).mark_line(point=True).encode(
                x='month:N',
                y='amount:Q',
                color=alt.Color('type:N', scale=alt.Scale(
                    domain=['income', 'expense'],
                    range=['#10b981', '#ef4444']
                ))
            ).properties(height=300)
            
            st.altair_chart(chart, use_container_width=True)
    
    with tab3:
        st.subheader("Budget Planning")
        st.info("Budget planning features coming soon!")
else:
    st.info("No transactions found. Add some transactions to see your financial overview!")
