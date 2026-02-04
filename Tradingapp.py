import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
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
        padding-left: 20px;
        padding-right: 20px;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 10px;
        border-radius: 5px;
    }
    .profit {
        color: #00c853;
        font-weight: bold;
    }
    .loss {
        color: #f44336;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=['Symbol', 'Quantity', 'Buy Price', 'Current Price', 'P&L', 'P&L %'])
if 'orders' not in st.session_state:
    st.session_state.orders = pd.DataFrame(columns=['Time', 'Symbol', 'Type', 'Quantity', 'Price', 'Status'])
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.00

# Helper functions
@st.cache_data(ttl=60)
def get_stock_data(symbol, period='1d', interval='5m'):
    """Fetch stock data from Yahoo Finance"""
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
    """Create candlestick chart with volume"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} Price', 'Volume')
    )
    
    # Candlestick chart
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
    
    # Volume bar chart
    colors = ['red' if close < open else 'green' 
              for close, open in zip(data['Close'], data['Open'])]
    
    fig.add_trace(
        go.Bar(x=data.index, y=data['Volume'], name='Volume', marker_color=colors),
        row=2, col=1
    )
    
    fig.update_layout(
        height=600,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig

def place_order(symbol, order_type, quantity, price):
    """Place a buy/sell order"""
    new_order = pd.DataFrame({
        'Time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'Symbol': [symbol],
        'Type': [order_type],
        'Quantity': [quantity],
        'Price': [price],
        'Status': ['Executed']
    })
    
    st.session_state.orders = pd.concat([new_order, st.session_state.orders], ignore_index=True)
    
    if order_type == 'BUY':
        # Update balance
        total_cost = quantity * price
        st.session_state.balance -= total_cost
        
        # Update portfolio
        if symbol in st.session_state.portfolio['Symbol'].values:
            idx = st.session_state.portfolio[st.session_state.portfolio['Symbol'] == symbol].index[0]
            existing_qty = st.session_state.portfolio.loc[idx, 'Quantity']
            existing_price = st.session_state.portfolio.loc[idx, 'Buy Price']
            
            # Calculate average price
            new_avg_price = ((existing_qty * existing_price) + (quantity * price)) / (existing_qty + quantity)
            st.session_state.portfolio.loc[idx, 'Quantity'] = existing_qty + quantity
            st.session_state.portfolio.loc[idx, 'Buy Price'] = new_avg_price
        else:
            new_position = pd.DataFrame({
                'Symbol': [symbol],
                'Quantity': [quantity],
                'Buy Price': [price],
                'Current Price': [price],
                'P&L': [0],
                'P&L %': [0]
            })
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_position], ignore_index=True)
    
    elif order_type == 'SELL':
        if symbol in st.session_state.portfolio['Symbol'].values:
            idx = st.session_state.portfolio[st.session_state.portfolio['Symbol'] == symbol].index[0]
            existing_qty = st.session_state.portfolio.loc[idx, 'Quantity']
            
            if quantity <= existing_qty:
                # Update balance
                total_credit = quantity * price
                st.session_state.balance += total_credit
                
                # Update portfolio
                st.session_state.portfolio.loc[idx, 'Quantity'] = existing_qty - quantity
                
                # Remove if quantity becomes 0
                if st.session_state.portfolio.loc[idx, 'Quantity'] == 0:
                    st.session_state.portfolio = st.session_state.portfolio.drop(idx).reset_index(drop=True)

def update_portfolio_prices():
    """Update current prices and P&L for portfolio"""
    if not st.session_state.portfolio.empty:
        for idx, row in st.session_state.portfolio.iterrows():
            info = get_stock_info(row['Symbol'])
            if info and 'currentPrice' in info:
                current_price = info['currentPrice']
                st.session_state.portfolio.loc[idx, 'Current Price'] = current_price
                
                pl = (current_price - row['Buy Price']) * row['Quantity']
                pl_percent = ((current_price - row['Buy Price']) / row['Buy Price']) * 100
                
                st.session_state.portfolio.loc[idx, 'P&L'] = pl
                st.session_state.portfolio.loc[idx, 'P&L %'] = pl_percent

# Sidebar
with st.sidebar:
    st.title("📈 Trading Platform")
    st.markdown("---")
    
    # Account Info
    st.subheader("Account Overview")
    st.metric("Available Balance", f"${st.session_state.balance:,.2f}")
    
    portfolio_value = 0
    if not st.session_state.portfolio.empty:
        portfolio_value = (st.session_state.portfolio['Current Price'] * st.session_state.portfolio['Quantity']).sum()
    
    total_pl = 0
    if not st.session_state.portfolio.empty:
        total_pl = st.session_state.portfolio['P&L'].sum()
    
    st.metric("Portfolio Value", f"${portfolio_value:,.2f}")
    st.metric("Total P&L", f"${total_pl:,.2f}", delta=f"{(total_pl/st.session_state.balance)*100:.2f}%" if st.session_state.balance > 0 else "0%")
    
    st.markdown("---")
    
    # Watchlist
    st.subheader("Watchlist")
    new_symbol = st.text_input("Add to Watchlist", placeholder="Enter symbol (e.g., AAPL)")
    if st.button("Add Symbol"):
        if new_symbol and new_symbol.upper() not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_symbol.upper())
            st.success(f"Added {new_symbol.upper()} to watchlist")
    
    for symbol in st.session_state.watchlist:
        info = get_stock_info(symbol)
        if info and 'currentPrice' in info:
            current_price = info['currentPrice']
            prev_close = info.get('previousClose', current_price)
            change = ((current_price - prev_close) / prev_close) * 100
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**{symbol}**")
            with col2:
                color = "profit" if change >= 0 else "loss"
                st.markdown(f'<p class="{color}">{change:+.2f}%</p>', unsafe_allow_html=True)

# Main content
st.title("Trading Dashboard")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Market Watch", "💼 Portfolio", "📝 Orders", "🔄 Trade"])

# Tab 1: Market Watch
with tab1:
    st.header("Market Overview")
    
    # Update portfolio prices
    update_portfolio_prices()
    
    # Market indices
    col1, col2, col3, col4 = st.columns(4)
    
    indices = {'^GSPC': 'S&P 500', '^DJI': 'Dow Jones', '^IXIC': 'NASDAQ', '^RUT': 'Russell 2000'}
    cols = [col1, col2, col3, col4]
    
    for idx, (symbol, name) in enumerate(indices.items()):
        data = get_stock_data(symbol, period='1d', interval='1m')
        if data is not None and not data.empty:
            current = data['Close'].iloc[-1]
            prev = data['Close'].iloc[0]
            change = ((current - prev) / prev) * 100
            
            with cols[idx]:
                st.metric(name, f"{current:,.2f}", f"{change:+.2f}%")
    
    st.markdown("---")
    
    # Stock chart
    selected_symbol = st.selectbox("Select Stock", st.session_state.watchlist)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        period = st.radio("Time Period", ['1d', '5d', '1mo', '3mo', '1y'], horizontal=True, index=0)
        
        interval_map = {'1d': '5m', '5d': '15m', '1mo': '1h', '3mo': '1d', '1y': '1d'}
        stock_data = get_stock_data(selected_symbol, period=period, interval=interval_map[period])
        
        if stock_data is not None and not stock_data.empty:
            chart = create_candlestick_chart(stock_data, selected_symbol)
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.error("Unable to fetch stock data")
    
    with col2:
        st.subheader("Stock Info")
        info = get_stock_info(selected_symbol)
        
        if info:
            st.metric("Current Price", f"${info.get('currentPrice', 'N/A')}")
            st.metric("Day High", f"${info.get('dayHigh', 'N/A')}")
            st.metric("Day Low", f"${info.get('dayLow', 'N/A')}")
            st.metric("Volume", f"{info.get('volume', 'N/A'):,}")
            st.metric("Market Cap", f"${info.get('marketCap', 0)/1e9:.2f}B" if 'marketCap' in info else "N/A")
            st.metric("PE Ratio", f"{info.get('trailingPE', 'N/A')}")

# Tab 2: Portfolio
with tab2:
    st.header("My Portfolio")
    
    if not st.session_state.portfolio.empty:
        # Display portfolio
        display_portfolio = st.session_state.portfolio.copy()
        display_portfolio['Current Price'] = display_portfolio['Current Price'].apply(lambda x: f"${x:.2f}")
        display_portfolio['Buy Price'] = display_portfolio['Buy Price'].apply(lambda x: f"${x:.2f}")
        display_portfolio['P&L'] = display_portfolio['P&L'].apply(lambda x: f"${x:.2f}")
        display_portfolio['P&L %'] = display_portfolio['P&L %'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(display_portfolio, use_container_width=True, hide_index=True)
        
        # Portfolio summary
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        total_invested = (st.session_state.portfolio['Buy Price'] * st.session_state.portfolio['Quantity']).sum()
        total_current = (st.session_state.portfolio['Current Price'] * st.session_state.portfolio['Quantity']).sum()
        total_pl = st.session_state.portfolio['P&L'].sum()
        
        with col1:
            st.metric("Total Invested", f"${total_invested:,.2f}")
        with col2:
            st.metric("Current Value", f"${total_current:,.2f}")
        with col3:
            pl_color = "normal" if total_pl >= 0 else "inverse"
            st.metric("Total Profit/Loss", f"${total_pl:,.2f}", 
                     delta=f"{(total_pl/total_invested)*100:.2f}%" if total_invested > 0 else "0%",
                     delta_color=pl_color)
    else:
        st.info("Your portfolio is empty. Start trading to see your holdings here.")

# Tab 3: Orders
with tab3:
    st.header("Order History")
    
    if not st.session_state.orders.empty:
        st.dataframe(st.session_state.orders, use_container_width=True, hide_index=True)
    else:
        st.info("No orders placed yet.")

# Tab 4: Trade
with tab4:
    st.header("Place Order")
    
    col1, col2 = st.columns(2)
    
    with col1:
        trade_symbol = st.selectbox("Select Stock", st.session_state.watchlist, key="trade_symbol")
        order_type = st.radio("Order Type", ["BUY", "SELL"], horizontal=True)
        
        info = get_stock_info(trade_symbol)
        current_price = info.get('currentPrice', 0) if info else 0
        
        st.info(f"Current Market Price: ${current_price:.2f}")
        
    with col2:
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
        price = st.number_input("Price per Share", min_value=0.01, value=float(current_price), step=0.01)
        
        total_value = quantity * price
        st.write(f"**Total Value:** ${total_value:,.2f}")
        
        if order_type == "BUY":
            if total_value > st.session_state.balance:
                st.error("Insufficient balance!")
            else:
                if st.button("Place Buy Order", type="primary", use_container_width=True):
                    place_order(trade_symbol, order_type, quantity, price)
                    st.success(f"Buy order placed successfully for {quantity} shares of {trade_symbol} at ${price:.2f}")
                    time.sleep(1)
                    st.rerun()
        else:
            can_sell = False
            if trade_symbol in st.session_state.portfolio['Symbol'].values:
                available_qty = st.session_state.portfolio[st.session_state.portfolio['Symbol'] == trade_symbol]['Quantity'].iloc[0]
                if quantity <= available_qty:
                    can_sell = True
                else:
                    st.error(f"Insufficient quantity! You have {available_qty} shares available.")
            else:
                st.error("You don't own this stock!")
            
            if can_sell:
                if st.button("Place Sell Order", type="primary", use_container_width=True):
                    place_order(trade_symbol, order_type, quantity, price)
                    st.success(f"Sell order placed successfully for {quantity} shares of {trade_symbol} at ${price:.2f}")
                    time.sleep(1)
                    st.rerun()

# Auto-refresh
if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

# Footer
st.markdown("---")
st.caption("📊 Trading Platform - Demo Version | Data provided by Yahoo Finance")
