# BTC Iron Condor Full Streamlit App with Greeks and Live Data + Fallback for scipy

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import requests
import pandas as pd
from datetime import datetime
import math

# === Safe import of scipy ===
try:
    from scipy.stats import norm
except ModuleNotFoundError:
    st.error("⚠️ The required module 'scipy' is not installed. Please run: pip install scipy")
    st.stop()

st.set_page_config(page_title="BTC Iron Condor Payoff Calculator", layout="wide")
st.title("BTC Iron Condor Payoff Calculator")

# === Fetch BTC live price ===
def fetch_live_btc_price():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        return res.json()['bitcoin']['usd']
    except:
        return 107200

# === Fetch option chain ===
def fetch_deribit_option_chain():
    url = "https://www.deribit.com/api/v2/public/get_instruments"
    params = {"currency": "BTC", "kind": "option", "expired": "false"}
    try:
        res = requests.get(url, params=params)
        data = res.json()['result']
        df = pd.DataFrame(data)
        df = df[['instrument_name', 'strike', 'option_type', 'expiration_timestamp', 'is_active']]
        df['expiration'] = pd.to_datetime(df['expiration_timestamp'], unit='ms')
        return df[df['is_active']].sort_values(by='strike')
    except:
        return pd.DataFrame()

# === Greeks Calculator ===
def calculate_greeks(S, K, T, r, sigma, option_type):
    d1 = (math.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        delta = norm.cdf(d1)
        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))) - r * K * math.exp(-r * T) * norm.cdf(d2)
        vega = S * norm.pdf(d1) * math.sqrt(T)
    elif option_type == "put":
        delta = -norm.cdf(-d1)
        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))) + r * K * math.exp(-r * T) * norm.cdf(-d2)
        vega = S * norm.pdf(d1) * math.sqrt(T)
    else:
        raise ValueError("Invalid option type")

    return {
        'Delta': round(delta, 4),
        'Gamma': round(gamma, 6),
        'Theta': round(theta / 365, 4),  # daily
        'Vega': round(vega / 100, 4)      # per 1% change in IV
    }

# === UI Sidebar ===
st.sidebar.header("Iron Condor Setup")
option_chain = fetch_deribit_option_chain()
unique_expiries = option_chain['expiration'].dt.date.unique() if not option_chain.empty else []
selected_expiry = st.sidebar.selectbox("Choose Expiry", unique_expiries) if len(unique_expiries) else None

if selected_expiry:
    filtered_chain = option_chain[option_chain['expiration'].dt.date == selected_expiry]
    st.subheader(f"Option Chain - {selected_expiry}")
    st.dataframe(filtered_chain[['strike', 'option_type']].reset_index(drop=True))
else:
    filtered_chain = pd.DataFrame()

live_price = fetch_live_btc_price()
strikes = sorted(filtered_chain['strike'].unique()) if not filtered_chain.empty else [100000, 102000, 112000, 114000]

put_sell_strike = st.sidebar.selectbox("Put Sell Strike", strikes, index=1)
put_buy_strike = st.sidebar.selectbox("Put Buy Strike", [s for s in strikes if s < put_sell_strike], index=0)
call_sell_strike = st.sidebar.selectbox("Call Sell Strike", strikes, index=-2)
call_buy_strike = st.sidebar.selectbox("Call Buy Strike", [s for s in strikes if s > call_sell_strike], index=0)

spot_price = st.sidebar.number_input("Spot Price", value=live_price)
put_sell_premium = st.sidebar.number_input("Put Sell Premium", value=420)
put_buy_premium = st.sidebar.number_input("Put Buy Premium", value=280)
call_sell_premium = st.sidebar.number_input("Call Sell Premium", value=400)
call_buy_premium = st.sidebar.number_input("Call Buy Premium", value=260)

risk_free_rate = st.sidebar.number_input("Risk-Free Rate (r)", value=0.05)
implied_vol = st.sidebar.number_input("Implied Volatility (IV %)", value=25.0) / 100

# === Strategy Calculations ===
total_credit = (put_sell_premium - put_buy_premium) + (call_sell_premium - call_buy_premium)
put_spread_width = put_sell_strike - put_buy_strike
call_spread_width = call_buy_strike - call_sell_strike
max_loss = max(put_spread_width, call_spread_width) - total_credit
break_even_low = put_sell_strike - total_credit
break_even_high = call_sell_strike + total_credit

# === Days to Expiry ===
if selected_expiry:
    today = datetime.utcnow().date()
    days_to_expiry = (selected_expiry - today).days
else:
    days_to_expiry = 7

# === Payoff Calculation ===
def calculate_payoff(price):
    put_payoff = np.where(price < put_sell_strike, np.minimum(put_sell_strike - price, put_spread_width), 0)
    put_protection = np.where(price < put_buy_strike, (put_buy_strike - price), 0)
    call_payoff = np.where(price > call_sell_strike, np.minimum(price - call_sell_strike, call_spread_width), 0)
    call_protection = np.where(price > call_buy_strike, (price - call_buy_strike), 0)
    return total_credit - (put_payoff - put_protection + call_payoff - call_protection)

price_range = np.linspace(spot_price - 10000, spot_price + 10000, 500)
payoff = calculate_payoff(price_range)

# === Greeks Display ===
st.subheader("Greeks Summary")
greek_data = {
    "Put Sell": calculate_greeks(spot_price, put_sell_strike, days_to_expiry / 365, risk_free_rate, implied_vol, 'put'),
    "Put Buy": calculate_greeks(spot_price, put_buy_strike, days_to_expiry / 365, risk_free_rate, implied_vol, 'put'),
    "Call Sell": calculate_greeks(spot_price, call_sell_strike, days_to_expiry / 365, risk_free_rate, implied_vol, 'call'),
    "Call Buy": calculate_greeks(spot_price, call_buy_strike, days_to_expiry / 365, risk_free_rate, implied_vol, 'call')
}

st.write(pd.DataFrame(greek_data).T)

# === Payoff Plot ===
st.subheader("Iron Condor Payoff Chart")
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(price_range, payoff, label='Payoff', color='orange')
ax.axhline(0, color='gray', linestyle='--')
ax.axvline(spot_price, color='blue', linestyle='--', label='Spot Price')
ax.axvline(put_sell_strike, color='green', linestyle='--', label='Put Sell Strike')
ax.axvline(call_sell_strike, color='red', linestyle='--', label='Call Sell Strike')
ax.fill_between(price_range, payoff, where=payoff>0, color='green', alpha=0.1)
ax.fill_between(price_range, payoff, where=payoff<0, color='red', alpha=0.1)
ax.set_title("Payoff at Expiry")
ax.set_xlabel("BTC Price")
ax.set_ylabel("Profit / Loss (USD)")
ax.legend()
ax.grid(True)
st.pyplot(fig)

# === Strategy Summary ===
st.subheader("Strategy Summary")
st.write(f"**Total Credit:** ${total_credit:.2f}")
st.write(f"**Max Loss:** ${max_loss:.2f}")
st.write(f"**Break-even Range:** ${break_even_low:.2f} to ${break_even_high:.2f}")

st.caption("Built using Streamlit + CoinGecko + Deribit + Black-Scholes")
