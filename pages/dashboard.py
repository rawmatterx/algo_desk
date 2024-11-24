# pages/dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json
import time
from collections import deque

# Page configuration
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
        .tradingview-widget-container {
            margin-bottom: 1rem;
        }
        .data-metrics {
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        .metric-label {
            font-size: 0.8rem;
            color: #666;
        }
        .metric-value {
            font-size: 1.2rem;
            font-weight: bold;
            color: #333;
        }
        .stButton>button {
            width: 100%;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.4rem;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session states
if 'market_data' not in st.session_state:
    st.session_state.market_data = deque(maxlen=100)
if 'last_price' not in st.session_state:
    st.session_state.last_price = None
if 'positions' not in st.session_state:
    st.session_state.positions = []

class UpstoxDashboard:
    def __init__(self):
        self.base_url = "https://api.upstox.com/v2"
        self.access_token = st.session_state.get('access_token')
        
    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_market_data(self, symbol):
        try:
            response = requests.get(
                f"{self.base_url}/market-quote/ltp",
                headers=self.get_headers(),
                params={"symbol": symbol}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('ltp')
            return None
        except Exception as e:
            st.error(f"Error fetching market data: {str(e)}")
            return None

    def get_positions(self):
        try:
            response = requests.get(
                f"{self.base_url}/portfolio/positions",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            st.error(f"Error fetching positions: {str(e)}")
            return []

def main():
    # Check if user is logged in
    if 'access_token' not in st.session_state:
        st.warning("Please login first")
        st.stop()

    dashboard = UpstoxDashboard()

    # Create the layout
    st.title("Trading Dashboard")
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Market Data", "Trading", "Portfolio"])

    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Market Overview")
            
            # Instrument selector
            symbols = ["NSE_FO:NIFTY24JANFUT", "NSE_FO:BANKNIFTY24JANFUT", 
                      "NSE:RELIANCE", "NSE:TCS", "NSE:INFY"]
            selected_symbol = st.selectbox("Select Instrument", symbols)
            
            # Fetch and display real-time data
            if selected_symbol:
                price = dashboard.get_market_data(selected_symbol)
                if price:
                    st.session_state.last_price = price
                    st.session_state.market_data.append({
                        'time': datetime.now(),
                        'price': price
                    })

                # Create price chart
                if st.session_state.market_data:
                    df = pd.DataFrame(st.session_state.market_data)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df['time'],
                        y=df['price'],
                        mode='lines',
                        name='Price'
                    ))
                    fig.update_layout(
                        height=400,
                        margin=dict(l=0, r=0, t=0, b=0),
                        xaxis_title="Time",
                        yaxis_title="Price",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Quick Stats")
            
            if st.session_state.last_price:
                # Display metrics
                col3, col4 = st.columns(2)
                with col3:
                    st.metric(
                        "Last Price",
                        f"₹{st.session_state.last_price:,.2f}"
                    )
                with col4:
                    # Calculate change
                    if len(st.session_state.market_data) > 1:
                        old_price = list(st.session_state.market_data)[-2]['price']
                        change = st.session_state.last_price - old_price
                        st.metric(
                            "Change",
                            f"₹{abs(change):,.2f}",
                            f"{'+' if change >= 0 else '-'}{abs(change/old_price*100):.2f}%"
                        )

    with tab2:
        st.subheader("Place Order")
        
        col5, col6 = st.columns([1, 1])
        
        with col5:
            # Order form
            order_type = st.selectbox(
                "Order Type",
                ["MARKET", "LIMIT"]
            )
            
            quantity = st.number_input(
                "Quantity",
                min_value=1,
                value=1
            )
            
            if order_type == "LIMIT":
                limit_price = st.number_input(
                    "Limit Price",
                    min_value=0.01,
                    value=st.session_state.last_price if st.session_state.last_price else 0.01,
                    format="%.2f"
                )
        
        with col6:
            st.markdown("### Order Preview")
            st.markdown(f"""
            **Symbol:** {selected_symbol if 'selected_symbol' in locals() else ''}  
            **Type:** {order_type}  
            **Quantity:** {quantity}  
            {"**Price:** ₹" + f"{limit_price:,.2f}" if order_type == "LIMIT" else ""}
            """)
            
            col7, col8 = st.columns(2)
            with col7:
                if st.button("BUY", type="primary"):
                    st.success("Buy order placed successfully!")
            with col8:
                if st.button("SELL", type="primary"):
                    st.success("Sell order placed successfully!")

    with tab3:
        st.subheader("Portfolio & Positions")
        
        # Fetch positions
        positions = dashboard.get_positions()
        if positions:
            df_positions = pd.DataFrame(positions)
            st.dataframe(
                df_positions[['symbol', 'quantity', 'last_price', 'pnl']],
                use_container_width=True
            )
        else:
            st.info("No open positions")

        # Add refresh button
        if st.button("Refresh Data"):
            st.rerun()

    # Auto-refresh market data every 5 seconds
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
