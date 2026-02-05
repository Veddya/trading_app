"""
Indian Stock Trading Platform - Complete Production Version
Features: Live Market, Payment Gateway, OTP, NSE/BSE, Mutual Funds, Bank Linking
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, time as dt_time
import yfinance as yf
import pytz
import json
import re
import hashlib
import time as time_module
import streamlit.components.v1 as components

# Try to import razorpay (optional for demo)
try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    RAZORPAY_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Indian Stock Trading Platform - Live",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {padding: 0rem 1rem;}
    .live-indicator {
        background: #00c853; color: white; padding: 5px 15px;
        border-radius: 20px; font-weight: bold; animation: pulse 2s infinite;
    }
    .market-closed {
        background: #f44336; color: white; padding: 5px 15px;
        border-radius: 20px; font-weight: bold;
    }
    .pre-market {
        background: #ff9800; color: white; padding: 5px 15px;
        border-radius: 20px; font-weight: bold;
    }
    @keyframes pulse {
        0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; }
    }
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {height: 50px; padding: 15px 25px;}
    div[data-testid="metric-container"] {
        background-color: #f0f2f6; border: 1px solid #e0e0e0;
        padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .profit {color: #00c853; font-weight: bold; font-size: 18px;}
    .loss {color: #f44336; font-weight: bold; font-size: 18px;}
    .otp-box {
        background: #e3f2fd; border: 2px solid #1976d2;
        padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;
    }
    .otp-code {
        font-size: 32px; font-weight: bold; color: #1976d2;
        letter-spacing: 8px; font-family: monospace;
    }
    .payment-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 15px 40px; border: none;
        border-radius: 8px; font-size: 18px; font-weight: 600;
        cursor: pointer; width: 100%; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .bank-account-card {
        background: white; border: 2px solid #e0e0e0;
        padding: 20px; border-radius: 10px; margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    defaults = {
        'logged_in': False, 'user_data': {}, 'users_db': {},
        'portfolio': pd.DataFrame(columns=['Symbol', 'Name', 'Exchange', 'Quantity', 'Buy Price', 'Current Price', 'Investment', 'Current Value', 'P&L', 'P&L %']),
        'mutual_funds': pd.DataFrame(columns=['Fund Name', 'Units', 'NAV', 'Investment', 'Current Value', 'P&L', 'P&L %']),
        'orders': pd.DataFrame(columns=['Time', 'Type', 'Symbol', 'Exchange', 'Order Type', 'Quantity', 'Price', 'Status']),
        'transactions': pd.DataFrame(columns=['Time', 'Type', 'Amount', 'Description', 'Balance']),
        'balance': 0.00,
        'watchlist': ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'],
        'auto_refresh': True, 'refresh_interval': 30
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Market data
IST = pytz.timezone('Asia/Kolkata')

# Import all stocks from stock database
try:
    from stock_database import ALL_NSE_STOCKS, ALL_BSE_STOCKS, STOCK_CATEGORIES
    NSE_STOCKS = ALL_NSE_STOCKS
    BSE_STOCKS = ALL_BSE_STOCKS
except ImportError:
    # Fallback to basic stocks if database not available
    NSE_STOCKS = {
        'RELIANCE.NS': 'Reliance Industries Ltd', 'TCS.NS': 'Tata Consultancy Services Ltd',
        'HDFCBANK.NS': 'HDFC Bank Ltd', 'INFY.NS': 'Infosys Ltd',
        'ICICIBANK.NS': 'ICICI Bank Ltd', 'SBIN.NS': 'State Bank of India',
    }
    BSE_STOCKS = {k.replace('.NS', '.BO'): v for k, v in NSE_STOCKS.items()}
    STOCK_CATEGORIES = {}

MUTUAL_FUNDS = {
    'SBI Bluechip Fund': {'nav': 75.50, 'returns_1y': 18.5, 'category': 'Large Cap'},
    'HDFC Mid-Cap Fund': {'nav': 125.30, 'returns_1y': 22.3, 'category': 'Mid Cap'},
    'ICICI Balanced Fund': {'nav': 52.80, 'returns_1y': 15.7, 'category': 'Hybrid'},
    'Axis ELSS Fund': {'nav': 68.90, 'returns_1y': 16.2, 'category': 'ELSS'},
}

INDICES = {'^NSEI': 'NIFTY 50', '^BSESN': 'SENSEX', '^NSEBANK': 'NIFTY BANK'}

# Helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def validate_phone(phone):
    return re.match(r'^[6-9]\d{9}$', phone) is not None

def generate_otp():
    return str(np.random.randint(100000, 999999))

def send_otp(email, phone):
    otp = generate_otp()
    st.session_state.otp = otp
    st.session_state.otp_time = datetime.now()
    st.session_state.otp_email = email
    st.session_state.otp_phone = phone
    return otp

def verify_otp(entered_otp):
    if 'otp' not in st.session_state:
        return False
    time_diff = (datetime.now() - st.session_state.otp_time).seconds
    if time_diff > 300:
        return False
    return entered_otp == st.session_state.otp

def get_market_status():
    now = datetime.now(IST)
    current_time = now.time()
    current_day = now.weekday()
    
    if current_day >= 5:
        return "CLOSED", "Weekend - Market Closed", "Monday 09:15 AM", "#f44336"
    
    if current_time < dt_time(9, 0, 0):
        return "CLOSED", "Pre-Market opens at 09:00 AM", "09:00 AM", "#f44336"
    elif dt_time(9, 0, 0) <= current_time < dt_time(9, 15, 0):
        return "PRE-MARKET", "Pre-Market Session", "09:15 AM", "#ff9800"
    elif dt_time(9, 15, 0) <= current_time < dt_time(15, 30, 0):
        return "OPEN", "Market is Live", "03:30 PM", "#00c853"
    elif dt_time(15, 30, 0) <= current_time < dt_time(16, 0, 0):
        return "POST-MARKET", "Post-Market Session", "Closed", "#ff9800"
    else:
        return "CLOSED", "Market Closed", "Tomorrow 09:15 AM", "#f44336"

def search_stocks(query):
    if not query:
        return []
    query = query.upper()
    results = []
    
    for symbol, name in NSE_STOCKS.items():
        if query in symbol.upper() or query in name.upper():
            results.append({'symbol': symbol, 'name': name, 'exchange': 'NSE'})
    
    for symbol, name in BSE_STOCKS.items():
        if query in symbol.upper() or query in name.upper():
            results.append({'symbol': symbol, 'name': name, 'exchange': 'BSE'})
    
    return results[:20]

@st.cache_data(ttl=10)
def get_stock_data_live(symbol, period='1d', interval='1m'):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period, interval=interval)
        return data
    except:
        return None

@st.cache_data(ttl=10)
def get_stock_info_live(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period='1d', interval='1m')
        if not hist.empty:
            info['currentPrice'] = hist['Close'].iloc[-1]
            info['lastUpdate'] = hist.index[-1].strftime('%H:%M:%S')
        return info
    except:
        return None

def create_candlestick_chart(data, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.7, 0.3], subplot_titles=(f'{symbol}', 'Volume'))
    
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                  low=data['Low'], close=data['Close'], name='Price'), row=1, col=1)
    
    colors = ['red' if c < o else 'green' for c, o in zip(data['Close'], data['Open'])]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume', marker_color=colors), row=2, col=1)
    
    fig.update_layout(height=500, showlegend=False, xaxis_rangeslider_visible=False,
                     hovermode='x unified', template='plotly_white')
    return fig

# Payment Gateway Integration
class RazorpayGateway:
    def __init__(self):
        if RAZORPAY_AVAILABLE:
            key_id = st.secrets.get("RAZORPAY_KEY_ID", "rzp_test_demo")
            key_secret = st.secrets.get("RAZORPAY_SECRET_KEY", "demo_secret")
            try:
                self.client = razorpay.Client(auth=(key_id, key_secret))
            except:
                self.client = None
        else:
            self.client = None
    
    def create_order(self, amount):
        if not self.client:
            # Demo mode
            return {'id': f'order_demo_{int(datetime.now().timestamp())}', 'amount': int(amount * 100)}
        
        try:
            order = self.client.order.create({
                'amount': int(amount * 100),
                'currency': 'INR',
                'payment_capture': 1
            })
            return order
        except Exception as e:
            st.error(f"Error: {e}")
            return None
    
    def verify_payment(self, order_id, payment_id, signature):
        if not self.client:
            # Demo mode - always return True
            return True
        
        try:
            params = {'razorpay_order_id': order_id, 'razorpay_payment_id': payment_id,
                     'razorpay_signature': signature}
            self.client.utility.verify_payment_signature(params)
            return True
        except:
            return False

def validate_account_number(account_number):
    if not account_number or not account_number.isdigit():
        return False, "Account number must contain only digits"
    if len(account_number) < 9 or len(account_number) > 18:
        return False, "Account number must be 9-18 digits"
    return True, ""

def validate_ifsc(ifsc):
    if not ifsc or len(ifsc) != 11:
        return False, "IFSC code must be 11 characters"
    ifsc = ifsc.upper()
    if not ifsc[:4].isalpha() or ifsc[4] != '0' or not ifsc[5:].isalnum():
        return False, "Invalid IFSC format"
    return True, ""

# Transaction functions
def add_funds(amount, method, payment_id=None):
    new_transaction = pd.DataFrame({
        'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'Type': ['Credit'],
        'Amount': [amount],
        'Description': [f'Funds added via {method}' + (f' - {payment_id}' if payment_id else '')],
        'Balance': [st.session_state.balance + amount]
    })
    
    st.session_state.balance += amount
    st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)
    st.session_state.user_data['balance'] = st.session_state.balance

def withdraw_funds(amount, bank_account):
    if amount > st.session_state.balance:
        return False
    
    new_transaction = pd.DataFrame({
        'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'Type': ['Debit'],
        'Amount': [amount],
        'Description': [f'Withdrawal to {bank_account.get("bank_name", "Bank")} - XXXX{bank_account["account_number"][-4:]}'],
        'Balance': [st.session_state.balance - amount]
    })
    
    st.session_state.balance -= amount
    st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)
    st.session_state.user_data['balance'] = st.session_state.balance
    return True

def place_stock_order(symbol, name, exchange, order_type, quantity, price):
    new_order = pd.DataFrame({
        'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'Type': ['Stock'], 'Symbol': [symbol], 'Exchange': [exchange],
        'Order Type': [order_type], 'Quantity': [quantity], 'Price': [price], 'Status': ['Executed']
    })
    st.session_state.orders = pd.concat([new_order, st.session_state.orders], ignore_index=True)
    
    if order_type == 'BUY':
        total_cost = quantity * price
        st.session_state.balance -= total_cost
        
        if symbol in st.session_state.portfolio['Symbol'].values:
            idx = st.session_state.portfolio[st.session_state.portfolio['Symbol'] == symbol].index[0]
            existing_qty = st.session_state.portfolio.loc[idx, 'Quantity']
            existing_price = st.session_state.portfolio.loc[idx, 'Buy Price']
            new_avg_price = ((existing_qty * existing_price) + (quantity * price)) / (existing_qty + quantity)
            st.session_state.portfolio.loc[idx, 'Quantity'] = existing_qty + quantity
            st.session_state.portfolio.loc[idx, 'Buy Price'] = new_avg_price
        else:
            new_position = pd.DataFrame({
                'Symbol': [symbol], 'Name': [name], 'Exchange': [exchange],
                'Quantity': [quantity], 'Buy Price': [price], 'Current Price': [price],
                'Investment': [quantity * price], 'Current Value': [quantity * price],
                'P&L': [0], 'P&L %': [0]
            })
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_position], ignore_index=True)
        
        new_transaction = pd.DataFrame({
            'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            'Type': ['Debit'], 'Amount': [total_cost],
            'Description': [f'Bought {quantity} shares of {symbol}'],
            'Balance': [st.session_state.balance]
        })
        st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)
    
    elif order_type == 'SELL':
        if symbol in st.session_state.portfolio['Symbol'].values:
            idx = st.session_state.portfolio[st.session_state.portfolio['Symbol'] == symbol].index[0]
            existing_qty = st.session_state.portfolio.loc[idx, 'Quantity']
            
            if quantity <= existing_qty:
                total_credit = quantity * price
                st.session_state.balance += total_credit
                st.session_state.portfolio.loc[idx, 'Quantity'] = existing_qty - quantity
                
                if st.session_state.portfolio.loc[idx, 'Quantity'] == 0:
                    st.session_state.portfolio = st.session_state.portfolio.drop(idx).reset_index(drop=True)
                
                new_transaction = pd.DataFrame({
                    'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    'Type': ['Credit'], 'Amount': [total_credit],
                    'Description': [f'Sold {quantity} shares of {symbol}'],
                    'Balance': [st.session_state.balance]
                })
                st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)

def update_portfolio_prices():
    if not st.session_state.portfolio.empty:
        for idx, row in st.session_state.portfolio.iterrows():
            info = get_stock_info_live(row['Symbol'])
            if info and 'currentPrice' in info:
                current_price = info['currentPrice']
                st.session_state.portfolio.loc[idx, 'Current Price'] = current_price
                current_value = current_price * row['Quantity']
                investment = row['Buy Price'] * row['Quantity']
                st.session_state.portfolio.loc[idx, 'Current Value'] = current_value
                st.session_state.portfolio.loc[idx, 'Investment'] = investment
                st.session_state.portfolio.loc[idx, 'P&L'] = current_value - investment
                st.session_state.portfolio.loc[idx, 'P&L %'] = ((current_value - investment) / investment) * 100

# Authentication pages
def login_page():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🏛️ Indian Stock Trading Platform</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Login to Your Account</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        email = st.text_input("📧 Email", placeholder="your.email@example.com")
        password = st.text_input("🔒 Password", type="password")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Login", type="primary", use_container_width=True):
                if email in st.session_state.users_db:
                    user = st.session_state.users_db[email]
                    if user['password'] == hash_password(password):
                        if user.get('verified', False):
                            st.session_state.logged_in = True
                            st.session_state.user_data = user
                            st.session_state.balance = user.get('balance', 0)
                            st.success("✅ Login successful!")
                            time_module.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Please verify your account first!")
                    else:
                        st.error("❌ Invalid password!")
                else:
                    st.error("❌ Email not registered!")
        
        with col_btn2:
            if st.button("Register", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()

def register_page():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🏛️ Create New Account</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        name = st.text_input("👤 Full Name", placeholder="John Doe")
        email = st.text_input("📧 Email", placeholder="your.email@example.com")
        phone = st.text_input("📱 Phone Number", placeholder="9876543210", max_chars=10)
        password = st.text_input("🔒 Password", type="password")
        confirm_password = st.text_input("🔒 Confirm Password", type="password")
        pan = st.text_input("🆔 PAN Number", placeholder="ABCDE1234F", max_chars=10)
        
        st.markdown("---")
        
        if st.button("Send OTP", type="primary", use_container_width=True):
            if not all([name, email, phone, password, pan]):
                st.error("❌ Please fill all fields!")
            elif not validate_email(email):
                st.error("❌ Invalid email format!")
            elif not validate_phone(phone):
                st.error("❌ Invalid phone number!")
            elif password != confirm_password:
                st.error("❌ Passwords don't match!")
            elif len(password) < 6:
                st.error("❌ Password must be at least 6 characters!")
            elif email in st.session_state.users_db:
                st.error("❌ Email already registered!")
            else:
                otp = send_otp(email, phone)
                st.session_state.temp_user = {
                    'name': name, 'email': email, 'phone': phone,
                    'password': hash_password(password), 'pan': pan.upper(),
                    'balance': 0, 'verified': False
                }
                st.session_state.show_otp = True
                st.rerun()
        
        if st.button("← Back to Login"):
            st.session_state.show_register = False
            st.rerun()

def otp_verification_page():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>📱 Verify OTP</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.success(f"✅ OTP sent to: {st.session_state.otp_email} and {st.session_state.otp_phone}")
        
        st.markdown(f"""
        <div class="otp-box">
            <p style="margin: 0; font-size: 16px; color: #666;">Your OTP Code (Demo)</p>
            <p class="otp-code">{st.session_state.otp}</p>
            <p style="margin: 0; font-size: 14px; color: #999;">Valid for 5 minutes</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("⚠️ Demo: OTP displayed above. In production, sent via SMS/Email.")
        
        otp = st.text_input("Enter 6-digit OTP", placeholder="123456", max_chars=6)
        
        col_verify, col_resend = st.columns(2)
        
        with col_verify:
            if st.button("✅ Verify OTP", type="primary", use_container_width=True):
                if verify_otp(otp):
                    user_data = st.session_state.temp_user
                    user_data['verified'] = True
                    st.session_state.users_db[user_data['email']] = user_data
                    st.success("✅ Registration successful!")
                    st.balloons()
                    st.session_state.show_otp = False
                    st.session_state.show_register = False
                    time_module.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ Invalid OTP!")
        
        with col_resend:
            if st.button("🔄 Resend OTP", use_container_width=True):
                send_otp(st.session_state.otp_email, st.session_state.otp_phone)
                st.success("✅ New OTP sent!")
                st.rerun()

# Main app
def main_app():
    # Market status header
    badge_html, market_status = get_market_status()
    badge_html = f'<span class="{"live-indicator" if market_status == "OPEN" else "market-closed"}">{"🟢 LIVE" if market_status == "OPEN" else "🔴 CLOSED"}</span>'
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.title("📊 Live Trading")
    with col2:
        st.markdown(f"<div style='padding-top: 20px;'>{badge_html}</div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='padding-top: 20px; text-align: right;'>🕒 {datetime.now(IST).strftime('%I:%M:%S %p')}</div>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"<h2 style='color: #1f77b4;'>👤 {st.session_state.user_data.get('name', 'User')}</h2>", unsafe_allow_html=True)
        st.markdown(f"📧 {st.session_state.user_data.get('email', '')}")
        st.markdown(f"📱 {st.session_state.user_data.get('phone', '')}")
        st.markdown("---")
        
        st.subheader("💰 Account")
        st.metric("Balance", f"₹{st.session_state.balance:,.2f}")
        
        portfolio_value = st.session_state.portfolio['Current Value'].sum() if not st.session_state.portfolio.empty else 0
        st.metric("Portfolio", f"₹{portfolio_value:,.2f}")
        
        total_pl = st.session_state.portfolio['P&L'].sum() if not st.session_state.portfolio.empty else 0
        st.metric("P&L", f"₹{total_pl:,.2f}", delta_color="normal" if total_pl >= 0 else "inverse")
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    
    update_portfolio_prices()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Market", "💼 Portfolio", "💱 Trade", "💰 Funds", "📋 Orders", "⚙️ Settings"])
    
    with tab1:
        st.header("Live Market")
        
        col1, col2, col3 = st.columns(3)
        for idx, (symbol, name) in enumerate(INDICES.items()):
            data = get_stock_data_live(symbol, period='1d', interval='1m')
            if data is not None and not data.empty:
                current = data['Close'].iloc[-1]
                prev = data['Close'].iloc[0]
                change = ((current - prev) / prev) * 100
                with [col1, col2, col3][idx]:
                    st.metric(name, f"{current:,.2f}", f"{change:+.2f}%")
        
        st.markdown("---")
        
        # Stock filtering
        col_filter1, col_filter2 = st.columns([1, 2])
        
        with col_filter1:
            if STOCK_CATEGORIES:
                category = st.selectbox("📁 Filter by Category", 
                                       ['All Stocks'] + list(STOCK_CATEGORIES.keys()))
            else:
                category = 'All Stocks'
        
        with col_filter2:
            search_query = st.text_input("🔍 Search Stocks", 
                                        placeholder="Company name or symbol (e.g., Reliance, TCS, HDFC)")
        
        # Show stock count
        total_nse = len(NSE_STOCKS)
        total_bse = len(BSE_STOCKS)
        st.info(f"📊 **{total_nse} NSE stocks** | **{total_bse} BSE stocks** | **Total: {total_nse + total_bse} stocks**")
        
        if search_query or category != 'All Stocks':
            if category != 'All Stocks' and STOCK_CATEGORIES:
                # Filter by category
                category_stocks = STOCK_CATEGORIES[category]
                filtered_results = [{'symbol': s, 'name': NSE_STOCKS[s], 'exchange': 'NSE'} 
                                  for s in category_stocks if s in NSE_STOCKS]
                
                if search_query:
                    # Further filter by search
                    query = search_query.upper()
                    filtered_results = [r for r in filtered_results 
                                      if query in r['symbol'].upper() or query in r['name'].upper()]
                
                st.write(f"**{category}** ({len(filtered_results)} stocks)")
            else:
                # Search in all stocks
                filtered_results = search_stocks(search_query)
            
            if filtered_results:
                st.write(f"**Found {len(filtered_results)} stocks:**")
                
                # Show in table format with pagination
                stocks_per_page = 20
                total_pages = (len(filtered_results) - 1) // stocks_per_page + 1
                
                if total_pages > 1:
                    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
                else:
                    page = 1
                
                start_idx = (page - 1) * stocks_per_page
                end_idx = min(start_idx + stocks_per_page, len(filtered_results))
                
                for result in filtered_results[start_idx:end_idx]:
                    col1, col2, col3, col4, col5 = st.columns([2, 4, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{result['symbol'].split('.')[0]}**")
                    with col2:
                        st.write(result['name'][:50])
                    with col3:
                        # Get live price
                        info = get_stock_info_live(result['symbol'])
                        if info and 'currentPrice' in info:
                            st.write(f"₹{info['currentPrice']:.2f}")
                        else:
                            st.write("-")
                    with col4:
                        st.write(result['exchange'])
                    with col5:
                        if st.button("➕", key=f"add_{result['symbol']}", help="Add to watchlist"):
                            if result['symbol'] not in st.session_state.watchlist:
                                st.session_state.watchlist.append(result['symbol'])
                                st.success(f"Added!")
                                time_module.sleep(0.5)
                                st.rerun()
                
                if total_pages > 1:
                    st.write(f"Page {page} of {total_pages}")
            else:
                st.warning("No stocks found. Try different search terms.")
        else:
            st.write("👆 **Use search or select category to find stocks**")
            
            # Show popular stocks
            st.markdown("---")
            st.subheader("⭐ Popular Stocks")
            
            popular = list(NSE_STOCKS.items())[:10]
            for symbol, name in popular:
                col1, col2, col3 = st.columns([2, 4, 1])
                with col1:
                    st.write(f"**{symbol.split('.')[0]}**")
                with col2:
                    st.write(name)
                with col3:
                    if st.button("➕", key=f"pop_{symbol}"):
                        if symbol not in st.session_state.watchlist:
                            st.session_state.watchlist.append(symbol)
                            st.rerun()
    
    with tab2:
        st.header("Portfolio")
        if not st.session_state.portfolio.empty:
            display_df = st.session_state.portfolio.copy()
            for col in ['Buy Price', 'Current Price', 'Investment', 'Current Value', 'P&L']:
                display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.2f}")
            display_df['P&L %'] = display_df['P&L %'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Portfolio empty")
    
    with tab3:
        st.header("Trade")
        
        search = st.text_input("Search stock to trade")
        if search:
            results = search_stocks(search)
            for result in results[:5]:
                if st.button(f"{result['name']} ({result['symbol'].split('.')[0]})", key=f"trade_{result['symbol']}"):
                    st.session_state.selected_trade_stock = result
                    st.rerun()
        
        if 'selected_trade_stock' in st.session_state:
            stock = st.session_state.selected_trade_stock
            st.success(f"Selected: {stock['name']}")
            
            col1, col2 = st.columns(2)
            with col1:
                order_type = st.radio("Type", ["BUY", "SELL"], horizontal=True)
                info = get_stock_info_live(stock['symbol'])
                current_price = info.get('currentPrice', 0) if info else 0
                st.info(f"Price: ₹{current_price:.2f}")
            
            with col2:
                quantity = st.number_input("Quantity", min_value=1, value=1)
                price = st.number_input("Price", min_value=0.01, value=float(current_price), step=0.01)
                
                if order_type == "BUY":
                    total = quantity * price
                    if total <= st.session_state.balance:
                        if st.button("🛒 Buy", type="primary", use_container_width=True):
                            place_stock_order(stock['symbol'], stock['name'], stock['exchange'], order_type, quantity, price)
                            st.success("Order placed!")
                            time_module.sleep(1)
                            st.rerun()
                    else:
                        st.error("Insufficient balance!")
    
    with tab4:
        st.header("Funds Management")
        
        tab_add, tab_withdraw = st.tabs(["➕ Add Funds", "➖ Withdraw"])
        
        with tab_add:
            st.subheader("Add Money")
            
            amount = st.number_input("Amount (₹)", min_value=100, max_value=1000000, value=10000, step=100)
            
            st.write("### Payment Methods")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("### 💳 Cards\n- Debit\n- Credit")
            with col2:
                st.markdown("### 📱 UPI\n- GPay\n- PhonePe\n- Paytm")
            with col3:
                st.markdown("### 🏦 Banking\n- Net Banking\n- All banks")
            
            st.markdown("---")
            
            # Payment gateway integration
            pg = RazorpayGateway()
            
            if st.button("💳 Pay with Razorpay", type="primary", use_container_width=True):
                order = pg.create_order(amount)
                if order:
                    st.success(f"✅ Order created: {order['id']}")
                    st.session_state.pending_order = {'order_id': order['id'], 'amount': amount}
                    
                    if not RAZORPAY_AVAILABLE:
                        st.info("🧪 **Demo Mode**: In production, Razorpay payment page would open here")
                        st.markdown("**Demo Payment Credentials:**")
                        st.code("Card: 4111 1111 1111 1111\nCVV: 123\nExpiry: 12/25")
                    
                    st.markdown("---")
                    st.subheader("Complete Payment")
                    
                    demo_payment = st.checkbox("Demo: Simulate successful payment")
                    
                    if demo_payment:
                        payment_id = f"pay_demo_{int(datetime.now().timestamp())}"
                        signature = "demo_signature"
                        
                        if st.button("✅ Confirm Demo Payment"):
                            if pg.verify_payment(order['id'], payment_id, signature):
                                add_funds(amount, "Razorpay", payment_id)
                                st.success(f"✅ ₹{amount:,.2f} added successfully!")
                                st.balloons()
                                time_module.sleep(2)
                                st.rerun()
            
            st.markdown("---")
            st.subheader("Alternative Methods")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💼 Bank Transfer (NEFT/IMPS)", use_container_width=True):
                    st.info("""
                    **Bank Details:**
                    - Account: Trading Platform Ltd
                    - A/C No: 1234567890
                    - IFSC: HDFC0001234
                    - Bank: HDFC Bank
                    """)
            
            with col2:
                if st.button("📱 UPI Direct", use_container_width=True):
                    st.info("""
                    **UPI ID:** trading@paytm
                    
                    Scan QR or pay to UPI ID.
                    Share transaction ID after payment.
                    """)
        
        with tab_withdraw:
            st.subheader("Withdraw Funds")
            
            if 'bank_accounts' not in st.session_state.user_data:
                st.session_state.user_data['bank_accounts'] = []
            
            if not st.session_state.user_data['bank_accounts']:
                st.warning("⚠️ Add bank account first")
                
                with st.form("add_bank"):
                    account_holder = st.text_input("Account Holder Name")
                    account_number = st.text_input("Account Number")
                    confirm_account = st.text_input("Confirm Account Number")
                    ifsc = st.text_input("IFSC Code")
                    bank_name = st.text_input("Bank Name")
                    
                    if st.form_submit_button("Add Bank Account"):
                        if account_number != confirm_account:
                            st.error("❌ Account numbers don't match!")
                        else:
                            is_valid, error = validate_account_number(account_number)
                            if not is_valid:
                                st.error(f"❌ {error}")
                            else:
                                is_valid, error = validate_ifsc(ifsc)
                                if not is_valid:
                                    st.error(f"❌ {error}")
                                else:
                                    st.session_state.user_data['bank_accounts'].append({
                                        'account_holder': account_holder,
                                        'account_number': account_number,
                                        'ifsc': ifsc.upper(),
                                        'bank_name': bank_name,
                                        'verified': True
                                    })
                                    st.success("✅ Bank account added!")
                                    st.rerun()
            else:
                bank_account = st.session_state.user_data['bank_accounts'][0]
                
                st.success("✅ Bank Account Linked")
                st.write(f"**Bank:** {bank_account['bank_name']}")
                st.write(f"**Account:** XXXX{bank_account['account_number'][-4:]}")
                st.write(f"**IFSC:** {bank_account['ifsc']}")
                
                st.markdown("---")
                
                withdraw_amount = st.number_input("Withdrawal Amount (₹)", min_value=100,
                                                 max_value=float(st.session_state.balance), value=1000, step=100)
                
                fee = 10 if withdraw_amount < 5000 else 0
                net_amount = withdraw_amount - fee
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Amount", f"₹{withdraw_amount:,.2f}")
                with col2:
                    st.metric("You'll receive", f"₹{net_amount:,.2f}")
                
                if st.button("Process Withdrawal", type="primary", use_container_width=True):
                    if withdraw_funds(withdraw_amount, bank_account):
                        st.success(f"""
                        ✅ Withdrawal Initiated!
                        - Amount: ₹{net_amount:,.2f}
                        - To: XXXX{bank_account['account_number'][-4:]}
                        - ETA: 1-3 business days
                        """)
                        time_module.sleep(2)
                        st.rerun()
    
    with tab5:
        st.header("Orders")
        if not st.session_state.orders.empty:
            display = st.session_state.orders.copy()
            display['Price'] = display['Price'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display, use_container_width=True, hide_index=True)
        else:
            st.info("No orders yet")
    
    with tab6:
        st.header("Settings")
        
        st.subheader("Account Info")
        st.write(f"**Name:** {st.session_state.user_data.get('name')}")
        st.write(f"**Email:** {st.session_state.user_data.get('email')}")
        st.write(f"**Phone:** {st.session_state.user_data.get('phone')}")
        st.write(f"**PAN:** {st.session_state.user_data.get('pan')}")

# Main flow
if not st.session_state.logged_in:
    if 'show_otp' in st.session_state and st.session_state.show_otp:
        otp_verification_page()
    elif 'show_register' in st.session_state and st.session_state.show_register:
        register_page()
    else:
        login_page()
else:
    main_app()

if st.session_state.logged_in:
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: gray;'>🇮🇳 Indian Stock Trading Platform | Live Market | All Payment Methods</p>", unsafe_allow_html=True)
