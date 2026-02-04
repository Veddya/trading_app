import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf
import json
import re
import hashlib
import time

# Page configuration
st.set_page_config(
    page_title="Indian Stock Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 15px 25px;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .profit {
        color: #00c853;
        font-weight: bold;
        font-size: 18px;
    }
    .loss {
        color: #f44336;
        font-weight: bold;
        font-size: 18px;
    }
    .stock-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin: 10px 0;
    }
    .header-text {
        color: #1f77b4;
        font-size: 24px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = {}
    if 'users_db' not in st.session_state:
        st.session_state.users_db = {}
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = pd.DataFrame(columns=['Symbol', 'Name', 'Exchange', 'Quantity', 'Buy Price', 'Current Price', 'Investment', 'Current Value', 'P&L', 'P&L %'])
    if 'mutual_funds' not in st.session_state:
        st.session_state.mutual_funds = pd.DataFrame(columns=['Fund Name', 'Units', 'NAV', 'Investment', 'Current Value', 'P&L', 'P&L %'])
    if 'orders' not in st.session_state:
        st.session_state.orders = pd.DataFrame(columns=['Time', 'Type', 'Symbol', 'Exchange', 'Order Type', 'Quantity', 'Price', 'Status'])
    if 'transactions' not in st.session_state:
        st.session_state.transactions = pd.DataFrame(columns=['Time', 'Type', 'Amount', 'Description', 'Balance'])
    if 'balance' not in st.session_state:
        st.session_state.balance = 0.00
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = [
            'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
            'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'WIPRO.NS', 'LT.NS'
        ]

init_session_state()

# Predefined stocks and mutual funds
INDIAN_STOCKS = {
    'NSE': {
        'RELIANCE.NS': 'Reliance Industries',
        'TCS.NS': 'Tata Consultancy Services',
        'HDFCBANK.NS': 'HDFC Bank',
        'INFY.NS': 'Infosys',
        'ICICIBANK.NS': 'ICICI Bank',
        'HINDUNILVR.NS': 'Hindustan Unilever',
        'SBIN.NS': 'State Bank of India',
        'BHARTIARTL.NS': 'Bharti Airtel',
        'ITC.NS': 'ITC Limited',
        'KOTAKBANK.NS': 'Kotak Mahindra Bank',
        'LT.NS': 'Larsen & Toubro',
        'AXISBANK.NS': 'Axis Bank',
        'ASIANPAINT.NS': 'Asian Paints',
        'MARUTI.NS': 'Maruti Suzuki',
        'TITAN.NS': 'Titan Company',
        'WIPRO.NS': 'Wipro',
        'TATAMOTORS.NS': 'Tata Motors',
        'ULTRACEMCO.NS': 'UltraTech Cement',
        'SUNPHARMA.NS': 'Sun Pharmaceutical',
        'NESTLEIND.NS': 'Nestle India',
    },
    'BSE': {
        'RELIANCE.BO': 'Reliance Industries',
        'TCS.BO': 'Tata Consultancy Services',
        'HDFCBANK.BO': 'HDFC Bank',
        'INFY.BO': 'Infosys',
        'ICICIBANK.BO': 'ICICI Bank',
    }
}

MUTUAL_FUNDS = {
    'SBI Bluechip Fund': {'nav': 75.50, 'returns_1y': 18.5, 'category': 'Large Cap'},
    'HDFC Mid-Cap Opportunities Fund': {'nav': 125.30, 'returns_1y': 22.3, 'category': 'Mid Cap'},
    'ICICI Prudential Balanced Advantage Fund': {'nav': 52.80, 'returns_1y': 15.7, 'category': 'Hybrid'},
    'Axis Long Term Equity Fund': {'nav': 68.90, 'returns_1y': 16.2, 'category': 'ELSS'},
    'Kotak Emerging Equity Fund': {'nav': 85.40, 'returns_1y': 25.8, 'category': 'Small Cap'},
    'UTI Nifty Index Fund': {'nav': 142.60, 'returns_1y': 14.5, 'category': 'Index Fund'},
    'Mirae Asset Large Cap Fund': {'nav': 95.20, 'returns_1y': 19.1, 'category': 'Large Cap'},
    'Parag Parikh Flexi Cap Fund': {'nav': 78.30, 'returns_1y': 21.4, 'category': 'Flexi Cap'},
}

INDICES = {
    '^NSEI': 'NIFTY 50',
    '^BSESN': 'SENSEX',
    '^NSEBANK': 'NIFTY BANK',
}

# Helper functions
def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate Indian phone number"""
    pattern = r'^[6-9]\d{9}$'
    return re.match(pattern, phone) is not None

def send_otp(contact, contact_type):
    """Simulate OTP sending"""
    otp = str(np.random.randint(100000, 999999))
    st.session_state.otp = otp
    st.session_state.otp_time = datetime.now()
    return otp

def verify_otp(entered_otp):
    """Verify OTP"""
    if 'otp' not in st.session_state:
        return False
    
    time_diff = (datetime.now() - st.session_state.otp_time).seconds
    if time_diff > 300:  # 5 minutes expiry
        return False
    
    return entered_otp == st.session_state.otp

@st.cache_data(ttl=60)
def get_stock_data(symbol, period='1d', interval='5m'):
    """Fetch stock data"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period, interval=interval)
        return data
    except:
        return None

@st.cache_data(ttl=60)
def get_stock_info(symbol):
    """Get current stock information"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return info
    except:
        return None

def create_candlestick_chart(data, symbol):
    """Create candlestick chart"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol}', 'Volume')
    )
    
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    colors = ['red' if close < open else 'green' 
              for close, open in zip(data['Close'], data['Open'])]
    
    fig.add_trace(
        go.Bar(x=data.index, y=data['Volume'], name='Volume', marker_color=colors),
        row=2, col=1
    )
    
    fig.update_layout(
        height=500,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig

def add_funds(amount, method):
    """Add funds to account"""
    new_transaction = pd.DataFrame({
        'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'Type': ['Credit'],
        'Amount': [amount],
        'Description': [f'Funds added via {method}'],
        'Balance': [st.session_state.balance + amount]
    })
    
    st.session_state.balance += amount
    st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)
    st.session_state.user_data['balance'] = st.session_state.balance

def withdraw_funds(amount, method):
    """Withdraw funds from account"""
    if amount > st.session_state.balance:
        return False
    
    new_transaction = pd.DataFrame({
        'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'Type': ['Debit'],
        'Amount': [amount],
        'Description': [f'Funds withdrawn via {method}'],
        'Balance': [st.session_state.balance - amount]
    })
    
    st.session_state.balance -= amount
    st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)
    st.session_state.user_data['balance'] = st.session_state.balance
    return True

def place_stock_order(symbol, name, exchange, order_type, quantity, price):
    """Place stock order"""
    new_order = pd.DataFrame({
        'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'Type': ['Stock'],
        'Symbol': [symbol],
        'Exchange': [exchange],
        'Order Type': [order_type],
        'Quantity': [quantity],
        'Price': [price],
        'Status': ['Executed']
    })
    
    st.session_state.orders = pd.concat([new_order, st.session_state.orders], ignore_index=True)
    
    if order_type == 'BUY':
        total_cost = quantity * price
        st.session_state.balance -= total_cost
        
        # Add to portfolio
        if symbol in st.session_state.portfolio['Symbol'].values:
            idx = st.session_state.portfolio[st.session_state.portfolio['Symbol'] == symbol].index[0]
            existing_qty = st.session_state.portfolio.loc[idx, 'Quantity']
            existing_price = st.session_state.portfolio.loc[idx, 'Buy Price']
            
            new_avg_price = ((existing_qty * existing_price) + (quantity * price)) / (existing_qty + quantity)
            st.session_state.portfolio.loc[idx, 'Quantity'] = existing_qty + quantity
            st.session_state.portfolio.loc[idx, 'Buy Price'] = new_avg_price
        else:
            new_position = pd.DataFrame({
                'Symbol': [symbol],
                'Name': [name],
                'Exchange': [exchange],
                'Quantity': [quantity],
                'Buy Price': [price],
                'Current Price': [price],
                'Investment': [quantity * price],
                'Current Value': [quantity * price],
                'P&L': [0],
                'P&L %': [0]
            })
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_position], ignore_index=True)
        
        # Add transaction
        new_transaction = pd.DataFrame({
            'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            'Type': ['Debit'],
            'Amount': [total_cost],
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
                
                # Add transaction
                new_transaction = pd.DataFrame({
                    'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    'Type': ['Credit'],
                    'Amount': [total_credit],
                    'Description': [f'Sold {quantity} shares of {symbol}'],
                    'Balance': [st.session_state.balance]
                })
                st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)

def buy_mutual_fund(fund_name, amount):
    """Buy mutual fund"""
    fund_info = MUTUAL_FUNDS[fund_name]
    nav = fund_info['nav']
    units = amount / nav
    
    if fund_name in st.session_state.mutual_funds['Fund Name'].values:
        idx = st.session_state.mutual_funds[st.session_state.mutual_funds['Fund Name'] == fund_name].index[0]
        existing_units = st.session_state.mutual_funds.loc[idx, 'Units']
        existing_investment = st.session_state.mutual_funds.loc[idx, 'Investment']
        
        st.session_state.mutual_funds.loc[idx, 'Units'] = existing_units + units
        st.session_state.mutual_funds.loc[idx, 'Investment'] = existing_investment + amount
    else:
        new_fund = pd.DataFrame({
            'Fund Name': [fund_name],
            'Units': [units],
            'NAV': [nav],
            'Investment': [amount],
            'Current Value': [amount],
            'P&L': [0],
            'P&L %': [0]
        })
        st.session_state.mutual_funds = pd.concat([st.session_state.mutual_funds, new_fund], ignore_index=True)
    
    st.session_state.balance -= amount
    
    # Add transaction
    new_transaction = pd.DataFrame({
        'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'Type': ['Debit'],
        'Amount': [amount],
        'Description': [f'Invested in {fund_name}'],
        'Balance': [st.session_state.balance]
    })
    st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)

def redeem_mutual_fund(fund_name, units):
    """Redeem mutual fund units"""
    if fund_name in st.session_state.mutual_funds['Fund Name'].values:
        idx = st.session_state.mutual_funds[st.session_state.mutual_funds['Fund Name'] == fund_name].index[0]
        available_units = st.session_state.mutual_funds.loc[idx, 'Units']
        
        if units <= available_units:
            nav = MUTUAL_FUNDS[fund_name]['nav']
            redemption_amount = units * nav
            
            st.session_state.mutual_funds.loc[idx, 'Units'] = available_units - units
            
            if st.session_state.mutual_funds.loc[idx, 'Units'] == 0:
                st.session_state.mutual_funds = st.session_state.mutual_funds.drop(idx).reset_index(drop=True)
            
            st.session_state.balance += redemption_amount
            
            # Add transaction
            new_transaction = pd.DataFrame({
                'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                'Type': ['Credit'],
                'Amount': [redemption_amount],
                'Description': [f'Redeemed {units:.2f} units of {fund_name}'],
                'Balance': [st.session_state.balance]
            })
            st.session_state.transactions = pd.concat([new_transaction, st.session_state.transactions], ignore_index=True)
            return True
    return False

def update_portfolio_prices():
    """Update current prices and P&L"""
    if not st.session_state.portfolio.empty:
        for idx, row in st.session_state.portfolio.iterrows():
            info = get_stock_info(row['Symbol'])
            if info and 'currentPrice' in info:
                current_price = info['currentPrice']
                st.session_state.portfolio.loc[idx, 'Current Price'] = current_price
                
                current_value = current_price * row['Quantity']
                investment = row['Buy Price'] * row['Quantity']
                
                st.session_state.portfolio.loc[idx, 'Current Value'] = current_value
                st.session_state.portfolio.loc[idx, 'Investment'] = investment
                st.session_state.portfolio.loc[idx, 'P&L'] = current_value - investment
                st.session_state.portfolio.loc[idx, 'P&L %'] = ((current_value - investment) / investment) * 100

def update_mutual_fund_values():
    """Update mutual fund values"""
    if not st.session_state.mutual_funds.empty:
        for idx, row in st.session_state.mutual_funds.iterrows():
            fund_name = row['Fund Name']
            current_nav = MUTUAL_FUNDS[fund_name]['nav'] * (1 + np.random.uniform(-0.02, 0.02))
            
            st.session_state.mutual_funds.loc[idx, 'NAV'] = current_nav
            current_value = current_nav * row['Units']
            st.session_state.mutual_funds.loc[idx, 'Current Value'] = current_value
            
            pl = current_value - row['Investment']
            pl_percent = (pl / row['Investment']) * 100 if row['Investment'] > 0 else 0
            
            st.session_state.mutual_funds.loc[idx, 'P&L'] = pl
            st.session_state.mutual_funds.loc[idx, 'P&L %'] = pl_percent

# Authentication Pages
def login_page():
    """Login page"""
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
                            st.success("Login successful!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Please verify your email and phone first!")
                    else:
                        st.error("Invalid password!")
                else:
                    st.error("Email not registered!")
        
        with col_btn2:
            if st.button("Register", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()

def register_page():
    """Registration page"""
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
            if not name or not email or not phone or not password or not pan:
                st.error("Please fill all fields!")
            elif not validate_email(email):
                st.error("Invalid email format!")
            elif not validate_phone(phone):
                st.error("Invalid phone number! Must be 10 digits starting with 6-9")
            elif password != confirm_password:
                st.error("Passwords don't match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters!")
            elif email in st.session_state.users_db:
                st.error("Email already registered!")
            else:
                # Send OTP
                email_otp = send_otp(email, 'email')
                phone_otp = send_otp(phone, 'phone')
                
                st.session_state.temp_user = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'password': hash_password(password),
                    'pan': pan.upper(),
                    'balance': 0,
                    'verified': False
                }
                
                st.success(f"OTP sent to email and phone!")
                st.info(f"Demo OTP (for testing): {email_otp}")
                st.session_state.show_otp = True
                st.rerun()
        
        if st.button("← Back to Login"):
            st.session_state.show_register = False
            st.rerun()

def otp_verification_page():
    """OTP verification page"""
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>📱 Verify OTP</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info(f"OTP sent to: {st.session_state.temp_user['email']} and {st.session_state.temp_user['phone']}")
        
        otp = st.text_input("Enter OTP", placeholder="123456", max_chars=6)
        
        if st.button("Verify OTP", type="primary", use_container_width=True):
            if verify_otp(otp):
                # Register user
                user_data = st.session_state.temp_user
                user_data['verified'] = True
                st.session_state.users_db[user_data['email']] = user_data
                
                st.success("✅ Registration successful! Please login.")
                st.session_state.show_otp = False
                st.session_state.show_register = False
                del st.session_state.temp_user
                time.sleep(2)
                st.rerun()
            else:
                st.error("Invalid or expired OTP!")
        
        if st.button("← Back"):
            st.session_state.show_otp = False
            st.rerun()

# Main App
def main_app():
    """Main trading application"""
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"<h2 style='color: #1f77b4;'>👤 {st.session_state.user_data.get('name', 'User')}</h2>", unsafe_allow_html=True)
        st.markdown(f"📧 {st.session_state.user_data.get('email', '')}")
        st.markdown(f"📱 {st.session_state.user_data.get('phone', '')}")
        st.markdown("---")
        
        # Account Overview
        st.subheader("💰 Account Overview")
        st.metric("Available Balance", f"₹{st.session_state.balance:,.2f}")
        
        portfolio_value = 0
        if not st.session_state.portfolio.empty:
            portfolio_value = st.session_state.portfolio['Current Value'].sum()
        
        mf_value = 0
        if not st.session_state.mutual_funds.empty:
            mf_value = st.session_state.mutual_funds['Current Value'].sum()
        
        total_value = st.session_state.balance + portfolio_value + mf_value
        
        st.metric("Portfolio Value", f"₹{portfolio_value:,.2f}")
        st.metric("Mutual Funds", f"₹{mf_value:,.2f}")
        st.metric("Total Assets", f"₹{total_value:,.2f}")
        
        total_pl = 0
        if not st.session_state.portfolio.empty:
            total_pl += st.session_state.portfolio['P&L'].sum()
        if not st.session_state.mutual_funds.empty:
            total_pl += st.session_state.mutual_funds['P&L'].sum()
        
        pl_color = "normal" if total_pl >= 0 else "inverse"
        st.metric("Total P&L", f"₹{total_pl:,.2f}", delta_color=pl_color)
        
        st.markdown("---")
        
        # Watchlist
        st.subheader("⭐ Watchlist")
        
        for symbol in st.session_state.watchlist[:5]:
            info = get_stock_info(symbol)
            if info and 'currentPrice' in info:
                current_price = info['currentPrice']
                prev_close = info.get('previousClose', current_price)
                change = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    stock_name = INDIAN_STOCKS['NSE'].get(symbol, symbol.replace('.NS', ''))
                    st.write(f"**{stock_name.split()[0]}**")
                with col2:
                    color = "profit" if change >= 0 else "loss"
                    st.markdown(f'<p class="{color}">{change:+.2f}%</p>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_data = {}
            st.rerun()
    
    # Main content
    st.title("📊 Indian Stock Trading Platform")
    
    # Update prices
    update_portfolio_prices()
    update_mutual_fund_values()
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Market", "💼 Portfolio", "🎯 Mutual Funds", "💱 Trade", "💰 Funds", "📋 Orders", "⚙️ Settings"
    ])
    
    # Tab 1: Market
    with tab1:
        st.header("Market Overview")
        
        # Indices
        col1, col2, col3 = st.columns(3)
        
        for idx, (symbol, name) in enumerate(INDICES.items()):
            data = get_stock_data(symbol, period='1d', interval='5m')
            if data is not None and not data.empty:
                current = data['Close'].iloc[-1]
                prev = data['Close'].iloc[0]
                change = ((current - prev) / prev) * 100
                
                with [col1, col2, col3][idx]:
                    st.metric(name, f"₹{current:,.2f}", f"{change:+.2f}%")
        
        st.markdown("---")
        
        # Stock selection
        col1, col2 = st.columns([1, 1])
        
        with col1:
            exchange = st.selectbox("Exchange", ['NSE', 'BSE'])
        
        with col2:
            stock_options = list(INDIAN_STOCKS[exchange].keys())
            selected_stock = st.selectbox("Select Stock", stock_options, 
                                         format_func=lambda x: f"{INDIAN_STOCKS[exchange][x]} ({x.split('.')[0]})")
        
        # Chart and info
        col1, col2 = st.columns([3, 1])
        
        with col1:
            period = st.radio("Period", ['1d', '5d', '1mo', '3mo', '1y'], horizontal=True)
            
            interval_map = {'1d': '5m', '5d': '15m', '1mo': '1h', '3mo': '1d', '1y': '1d'}
            stock_data = get_stock_data(selected_stock, period=period, interval=interval_map[period])
            
            if stock_data is not None and not stock_data.empty:
                chart = create_candlestick_chart(stock_data, INDIAN_STOCKS[exchange][selected_stock])
                st.plotly_chart(chart, use_container_width=True)
            else:
                st.error("Unable to fetch stock data")
        
        with col2:
            st.subheader("Stock Info")
            info = get_stock_info(selected_stock)
            
            if info:
                st.metric("LTP", f"₹{info.get('currentPrice', 0):,.2f}")
                st.metric("Day High", f"₹{info.get('dayHigh', 0):,.2f}")
                st.metric("Day Low", f"₹{info.get('dayLow', 0):,.2f}")
                st.metric("Volume", f"{info.get('volume', 0):,}")
                
                if 'marketCap' in info:
                    st.metric("Market Cap", f"₹{info['marketCap']/1e7:.2f}Cr")
                
                if selected_stock not in st.session_state.watchlist:
                    if st.button("⭐ Add to Watchlist", use_container_width=True):
                        st.session_state.watchlist.append(selected_stock)
                        st.success("Added to watchlist!")
                        st.rerun()
    
    # Tab 2: Portfolio
    with tab2:
        st.header("My Portfolio")
        
        if not st.session_state.portfolio.empty:
            display_df = st.session_state.portfolio.copy()
            
            # Format columns
            for col in ['Buy Price', 'Current Price', 'Investment', 'Current Value', 'P&L']:
                display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.2f}")
            display_df['P&L %'] = display_df['P&L %'].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Summary
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            total_invested = st.session_state.portfolio['Investment'].sum()
            total_current = st.session_state.portfolio['Current Value'].sum()
            total_pl = st.session_state.portfolio['P&L'].sum()
            
            with col1:
                st.metric("Total Invested", f"₹{total_invested:,.2f}")
            with col2:
                st.metric("Current Value", f"₹{total_current:,.2f}")
            with col3:
                pl_color = "normal" if total_pl >= 0 else "inverse"
                st.metric("Total P&L", f"₹{total_pl:,.2f}", delta_color=pl_color)
            with col4:
                pl_percent = (total_pl / total_invested * 100) if total_invested > 0 else 0
                st.metric("Returns", f"{pl_percent:.2f}%")
        else:
            st.info("📊 Your portfolio is empty. Start trading to build your portfolio!")
    
    # Tab 3: Mutual Funds
    with tab3:
        st.header("Mutual Funds")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("My Mutual Funds")
            
            if not st.session_state.mutual_funds.empty:
                display_mf = st.session_state.mutual_funds.copy()
                
                for col in ['NAV', 'Investment', 'Current Value', 'P&L']:
                    display_mf[col] = display_mf[col].apply(lambda x: f"₹{x:,.2f}")
                display_mf['Units'] = display_mf['Units'].apply(lambda x: f"{x:.4f}")
                display_mf['P&L %'] = display_mf['P&L %'].apply(lambda x: f"{x:.2f}%")
                
                st.dataframe(display_mf, use_container_width=True, hide_index=True)
                
                # Summary
                total_invested = st.session_state.mutual_funds['Investment'].sum()
                total_current = st.session_state.mutual_funds['Current Value'].sum()
                total_pl = st.session_state.mutual_funds['P&L'].sum()
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Invested", f"₹{total_invested:,.2f}")
                with col_b:
                    st.metric("Current Value", f"₹{total_current:,.2f}")
                with col_c:
                    st.metric("P&L", f"₹{total_pl:,.2f}")
            else:
                st.info("No mutual fund investments yet.")
        
        with col2:
            st.subheader("Invest in Mutual Funds")
            
            fund_name = st.selectbox("Select Fund", list(MUTUAL_FUNDS.keys()))
            fund_info = MUTUAL_FUNDS[fund_name]
            
            st.info(f"**Category:** {fund_info['category']}")
            st.info(f"**Current NAV:** ₹{fund_info['nav']:.2f}")
            st.info(f"**1Y Returns:** {fund_info['returns_1y']:.2f}%")
            
            amount = st.number_input("Investment Amount (₹)", min_value=500, value=5000, step=500)
            units = amount / fund_info['nav']
            st.write(f"Units to be allocated: **{units:.4f}**")
            
            if st.button("💰 Invest Now", type="primary", use_container_width=True):
                if amount > st.session_state.balance:
                    st.error("Insufficient balance!")
                else:
                    buy_mutual_fund(fund_name, amount)
                    st.success(f"Successfully invested ₹{amount:,.2f} in {fund_name}")
                    time.sleep(1)
                    st.rerun()
            
            st.markdown("---")
            
            # Redeem
            if not st.session_state.mutual_funds.empty:
                st.subheader("Redeem Mutual Funds")
                
                owned_funds = st.session_state.mutual_funds['Fund Name'].tolist()
                redeem_fund = st.selectbox("Select Fund to Redeem", owned_funds, key="redeem_fund")
                
                if redeem_fund:
                    idx = st.session_state.mutual_funds[st.session_state.mutual_funds['Fund Name'] == redeem_fund].index[0]
                    available_units = st.session_state.mutual_funds.loc[idx, 'Units']
                    
                    st.write(f"Available Units: **{available_units:.4f}**")
                    
                    redeem_units = st.number_input("Units to Redeem", min_value=0.0001, max_value=float(available_units), 
                                                   value=float(available_units), step=0.0001, format="%.4f")
                    
                    redemption_amount = redeem_units * MUTUAL_FUNDS[redeem_fund]['nav']
                    st.write(f"Redemption Amount: **₹{redemption_amount:,.2f}**")
                    
                    if st.button("🔄 Redeem", use_container_width=True):
                        if redeem_mutual_fund(redeem_fund, redeem_units):
                            st.success(f"Successfully redeemed {redeem_units:.4f} units!")
                            time.sleep(1)
                            st.rerun()
    
    # Tab 4: Trade
    with tab4:
        st.header("Place Order")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Order Details")
            
            exchange = st.selectbox("Select Exchange", ['NSE', 'BSE'], key="trade_exchange")
            stock_list = list(INDIAN_STOCKS[exchange].keys())
            trade_symbol = st.selectbox("Select Stock", stock_list,
                                       format_func=lambda x: f"{INDIAN_STOCKS[exchange][x]} ({x.split('.')[0]})",
                                       key="trade_symbol")
            
            stock_name = INDIAN_STOCKS[exchange][trade_symbol]
            
            order_type = st.radio("Order Type", ["BUY", "SELL"], horizontal=True)
            
            info = get_stock_info(trade_symbol)
            current_price = info.get('currentPrice', 0) if info else 0
            
            st.info(f"💹 Current Market Price: ₹{current_price:.2f}")
        
        with col2:
            st.subheader("Quantity & Price")
            
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
            price = st.number_input("Price per Share (₹)", min_value=0.01, value=float(current_price), step=0.01)
            
            total_value = quantity * price
            
            st.write(f"### Total Value: ₹{total_value:,.2f}")
            
            if order_type == "BUY":
                brokerage = total_value * 0.0003  # 0.03% brokerage
                total_cost = total_value + brokerage
                st.write(f"Brokerage: ₹{brokerage:.2f}")
                st.write(f"**Total Cost: ₹{total_cost:,.2f}**")
                
                if total_cost > st.session_state.balance:
                    st.error(f"❌ Insufficient balance! Need ₹{total_cost - st.session_state.balance:,.2f} more")
                else:
                    if st.button("🛒 Place Buy Order", type="primary", use_container_width=True):
                        place_stock_order(trade_symbol, stock_name, exchange, order_type, quantity, price)
                        st.success(f"✅ Buy order placed for {quantity} shares of {stock_name}")
                        time.sleep(1)
                        st.rerun()
            
            else:  # SELL
                can_sell = False
                if trade_symbol in st.session_state.portfolio['Symbol'].values:
                    idx = st.session_state.portfolio[st.session_state.portfolio['Symbol'] == trade_symbol].index[0]
                    available_qty = st.session_state.portfolio.loc[idx, 'Quantity']
                    
                    if quantity <= available_qty:
                        can_sell = True
                        st.success(f"✅ Available quantity: {available_qty}")
                    else:
                        st.error(f"❌ Insufficient quantity! You have {available_qty} shares")
                else:
                    st.error("❌ You don't own this stock!")
                
                if can_sell:
                    brokerage = total_value * 0.0003
                    total_credit = total_value - brokerage
                    st.write(f"Brokerage: ₹{brokerage:.2f}")
                    st.write(f"**You will receive: ₹{total_credit:,.2f}**")
                    
                    if st.button("💸 Place Sell Order", type="primary", use_container_width=True):
                        place_stock_order(trade_symbol, stock_name, exchange, order_type, quantity, price)
                        st.success(f"✅ Sell order placed for {quantity} shares of {stock_name}")
                        time.sleep(1)
                        st.rerun()
    
    # Tab 5: Funds Management
    with tab5:
        st.header("Funds Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Add Funds")
            
            add_amount = st.number_input("Amount to Add (₹)", min_value=100, value=10000, step=100, key="add_amount")
            add_method = st.selectbox("Payment Method", ['UPI', 'Net Banking', 'Debit Card', 'Credit Card'], key="add_method")
            
            if st.button("➕ Add Funds", type="primary", use_container_width=True):
                add_funds(add_amount, add_method)
                st.success(f"✅ Successfully added ₹{add_amount:,.2f} to your account!")
                time.sleep(1)
                st.rerun()
        
        with col2:
            st.subheader("💸 Withdraw Funds")
            
            withdraw_amount = st.number_input("Amount to Withdraw (₹)", min_value=100, 
                                             max_value=float(st.session_state.balance), 
                                             value=min(1000, float(st.session_state.balance)), 
                                             step=100, key="withdraw_amount")
            withdraw_method = st.selectbox("Withdrawal Method", ['Bank Transfer', 'UPI'], key="withdraw_method")
            
            if st.button("➖ Withdraw Funds", use_container_width=True):
                if withdraw_funds(withdraw_amount, withdraw_method):
                    st.success(f"✅ Successfully withdrawn ₹{withdraw_amount:,.2f} from your account!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Insufficient balance!")
        
        st.markdown("---")
        st.subheader("📊 Transaction History")
        
        if not st.session_state.transactions.empty:
            display_trans = st.session_state.transactions.copy()
            display_trans['Amount'] = display_trans['Amount'].apply(lambda x: f"₹{x:,.2f}")
            display_trans['Balance'] = display_trans['Balance'].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(display_trans, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet.")
    
    # Tab 6: Orders
    with tab6:
        st.header("Order History")
        
        if not st.session_state.orders.empty:
            display_orders = st.session_state.orders.copy()
            display_orders['Price'] = display_orders['Price'].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(display_orders, use_container_width=True, hide_index=True)
        else:
            st.info("No orders placed yet.")
    
    # Tab 7: Settings
    with tab7:
        st.header("⚙️ Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Account Information")
            st.write(f"**Name:** {st.session_state.user_data.get('name', '')}")
            st.write(f"**Email:** {st.session_state.user_data.get('email', '')}")
            st.write(f"**Phone:** {st.session_state.user_data.get('phone', '')}")
            st.write(f"**PAN:** {st.session_state.user_data.get('pan', '')}")
            st.write(f"**Verification Status:** ✅ Verified" if st.session_state.user_data.get('verified') else "❌ Not Verified")
        
        with col2:
            st.subheader("📈 Portfolio Summary")
            
            total_stocks = len(st.session_state.portfolio) if not st.session_state.portfolio.empty else 0
            total_mf = len(st.session_state.mutual_funds) if not st.session_state.mutual_funds.empty else 0
            total_orders = len(st.session_state.orders) if not st.session_state.orders.empty else 0
            
            st.metric("Total Stocks", total_stocks)
            st.metric("Total Mutual Funds", total_mf)
            st.metric("Total Orders", total_orders)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎨 Preferences")
            
            # Theme (placeholder - Streamlit doesn't support dynamic theme changes easily)
            st.selectbox("Theme", ["Light", "Dark"], disabled=True)
            st.info("Theme customization coming soon!")
            
            # Notifications
            email_notif = st.checkbox("Email Notifications", value=True)
            sms_notif = st.checkbox("SMS Notifications", value=True)
        
        with col2:
            st.subheader("🔐 Security")
            
            if st.button("Change Password", use_container_width=True):
                st.info("Password change feature coming soon!")
            
            if st.button("Enable 2FA", use_container_width=True):
                st.info("Two-factor authentication coming soon!")
        
        st.markdown("---")
        
        # Watchlist Management
        st.subheader("⭐ Manage Watchlist")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.session_state.watchlist:
                for i, symbol in enumerate(st.session_state.watchlist):
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        stock_name = INDIAN_STOCKS['NSE'].get(symbol, symbol)
                        st.write(f"{i+1}. {stock_name} ({symbol})")
                    with col_b:
                        if st.button("❌", key=f"remove_{symbol}"):
                            st.session_state.watchlist.remove(symbol)
                            st.rerun()
        
        with col2:
            st.write("Add new stocks from the Market tab")

# Main Application Flow
if not st.session_state.logged_in:
    if 'show_otp' in st.session_state and st.session_state.show_otp:
        otp_verification_page()
    elif 'show_register' in st.session_state and st.session_state.show_register:
        register_page()
    else:
        login_page()
else:
    main_app()

# Footer
if st.session_state.logged_in:
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: gray;'>🇮🇳 Indian Stock Trading Platform | NSE • BSE • Mutual Funds | Secure & Reliable</p>", unsafe_allow_html=True)
