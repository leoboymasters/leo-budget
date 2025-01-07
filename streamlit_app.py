import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import altair as alt
import traceback

# Page configuration
st.set_page_config(
    page_title="Budget Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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

# Initialize Google Sheets connection
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
            worksheet = spreadsheet.add_worksheet(title="Transactions", rows="1000", cols="5")
            headers = ["date", "description", "amount", "category", "type"]
            worksheet.append_row(headers)
        return True
    except Exception as e:
        st.error(f"Error ensuring worksheet exists: {str(e)}")
        return False

def add_transaction(date, description, amount, category, type_):
    try:
        if not ensure_worksheet_exists():
            return False
        client = init_google_sheets()
        sheet = client.open_by_key(st.secrets["spreadsheet_id"]).worksheet("Transactions")
        row = [date, description, amount, category, type_]
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
    st.title("Budget Pro")
    
    # Add transaction form
    st.subheader("Add Transaction")
    with st.form("transaction_form"):
        description = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        category = st.selectbox(
            "Category",
            ["Income", "Housing", "Food", "Transportation", "Entertainment", "Utilities"]
        )
        date = st.date_input("Date", datetime.now())
        
        submitted = st.form_submit_button("Add Transaction")
        
        if submitted and description and amount:
            transaction_type = "income" if category == "Income" else "expense"
            if add_transaction(
                date.strftime('%Y-%m-%d'),
                description,
                amount,
                category,
                transaction_type
            ):
                st.success("Transaction added!")
                st.experimental_rerun()

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
                <div class="metric-value">$%.2f</div>
            </div>
        """ % balance, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-label">Total Income</div>
                <div class="metric-value income">$%.2f</div>
            </div>
        """ % total_income, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-label">Total Expenses</div>
                <div class="metric-value expense">$%.2f</div>
            </div>
        """ % total_expenses, unsafe_allow_html=True)

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Transactions", "Analytics", "Budget Planning"])
    
    with tab1:
        st.subheader("Recent Transactions")
        # Add filters
        col1, col2 = st.columns(2)
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
        
        # Filter and display transactions
        mask = (df['category'].isin(selected_categories)) & (df['type'].isin(transaction_type))
        filtered_df = df[mask].sort_values('date', ascending=False)
        
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )
    
    with tab2:
        st.subheader("Spending Analysis")
        
        # Monthly trend chart
        monthly_data = df.copy()
        monthly_data['date'] = pd.to_datetime(monthly_data['date'])
        monthly_data['month'] = monthly_data['date'].dt.strftime('%Y-%m')
        
        # Create separate charts for income and expenses
        monthly_summary = monthly_data.groupby(['month', 'type'])['amount'].sum().unstack()
        
        if 'expense' in monthly_summary.columns:
            monthly_summary['expense'] = monthly_summary['expense'].abs()
        
        chart_data = monthly_summary.reset_index()
        
        if not chart_data.empty:
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
        
        # Category breakdown
        expenses_by_category = df[df['type'] == 'expense'].groupby('category')['amount'].sum().abs()
        
        if not expenses_by_category.empty:
            st.subheader("Expenses by Category")
            chart = alt.Chart(expenses_by_category.reset_index()).mark_bar().encode(
                x='category:N',
                y='amount:Q',
                color=alt.Color('category:N', legend=None)
            ).properties(height=300)
            
            st.altair_chart(chart, use_container_width=True)
    
    with tab3:
        st.subheader("Budget Planning")
        st.info("Budget planning features coming soon!")
else:
    st.info("No transactions found. Add some transactions to see your financial overview!")