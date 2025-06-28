import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="BTC Iron Condor Payoff Calculator", layout="centered")
st.title("BTC Iron Condor Payoff Calculator")
st.markdown("""
Input your trade parameters below to visualize the Iron Condor options strategy.
The chart and key financial metrics will update based on your inputs.
""")

# === User Inputs ===
with st.sidebar:
    st.header("Input Parameters")
    spot_price = st.number_input("Spot Price", value=107200)
    put_sell_strike = st.number_input("Put Sell Strike", value=102000)
    put_buy_strike = st.number_input("Put Buy Strike", value=100000)
    call_sell_strike = st.number_input("Call Sell Strike", value=112000)
    call_buy_strike = st.number_input("Call Buy Strike", value=114000)
    put_sell_premium = st.number_input("Put Sell Premium", value=420)
    put_buy_premium = st.number_input("Put Buy Premium", value=280)
    call_sell_premium = st.number_input("Call Sell Premium", value=400)
    call_buy_premium = st.number_input("Call Buy Premium", value=260)

# === Calculations ===
total_credit = (put_sell_premium - put_buy_premium) + (call_sell_premium - call_buy_premium)
put_spread_width = put_sell_strike - put_buy_strike
call_spread_width = call_buy_strike - call_sell_strike
max_loss = max(put_spread_width, call_spread_width) - total_credit
break_even_low = put_sell_strike - total_credit
break_even_high = call_sell_strike + total_credit

# === Payoff Function ===
def calculate_payoff(price):
    put_payoff = np.where(price < put_sell_strike, np.minimum(put_sell_strike - price, put_spread_width), 0)
    put_protection = np.where(price < put_buy_strike, (put_buy_strike - price), 0)
    call_payoff = np.where(price > call_sell_strike, np.minimum(price - call_sell_strike, call_spread_width), 0)
    call_protection = np.where(price > call_buy_strike, (price - call_buy_strike), 0)
    return total_credit - (put_payoff - put_protection + call_payoff - call_protection)

price_range = np.linspace(spot_price - 10000, spot_price + 10000, 500)
payoff = calculate_payoff(price_range)

# === Plotting ===
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(price_range, payoff, label='Iron Condor Payoff', color='orange')
ax.axhline(0, color='gray', linestyle='--')
ax.axvline(spot_price, color='blue', linestyle='--', label='Spot Price')
ax.axvline(put_sell_strike, color='green', linestyle='--', label='Put Sell Strike')
ax.axvline(call_sell_strike, color='red', linestyle='--', label='Call Sell Strike')
ax.set_title("Payoff Chart at Expiry")
ax.set_xlabel("BTC Price at Expiry")
ax.set_ylabel("Profit / Loss (USD)")
ax.legend()
ax.grid(True)
st.pyplot(fig)

# === Output Summary ===
st.subheader("Strategy Summary")
st.write(f"**Net Credit Received:** ${total_credit:.2f}")
st.write(f"**Maximum Loss:** ${max_loss:.2f}")
st.write(f"**Break-even Range:** ${break_even_low:.2f} to ${break_even_high:.2f}")
st.caption("Built with love using Streamlit")
