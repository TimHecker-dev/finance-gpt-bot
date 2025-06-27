# -*- coding: utf-8 -*-
"""
Final Project: Interactive Finance Chatbot with GPT and External APIs

Features:
- Stock price queries & price charts via yfinance
- Company news via NewsAPI.org
- Exchange rates via Open Exchange Rates
- Explicit function for stock price history
- Advanced user guidance & error handling

Author: Tim Hecker
"""

import os
import json
import requests
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from openai import AzureOpenAI
import streamlit as st
import yfinance as yf
from datetime import datetime
from io import StringIO

# ========== 1. Load environment variables ==========
load_dotenv(dotenv_path="config.txt", override=True)
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_ENDPOINT = os.environ.get("AZURE_OPENAI_API_ENDPOINT")
OPENAI_API_VERSION = os.environ.get("OPENAI_API_VERSION")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
OPENEXCHANGE_API_KEY = os.environ.get("OPENEXCHANGE_API_KEY")

model = "gpt-4o"
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_API_ENDPOINT,
    api_version=OPENAI_API_VERSION,
    azure_deployment=model
)
SUPPORT_PHONE_NUMBER = "070-1234-5678"

# ========== 2. GPT Function Descriptions ==========
functions = [
    {
        "name": "get_stock_price",
        "description": "Returns the current stock price for a given ticker symbol or company name.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol or company name, e.g., AAPL or Apple."
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_stock_history",
        "description": "Shows the stock price history (closing prices for the last 7 days) for a given ticker symbol or company.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol or company name, e.g., TSLA or Tesla."
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_financial_news",
        "description": "Returns the latest news for a given company or ticker.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol or company name, e.g., AAPL or Apple."
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_exchange_rate",
        "description": "Returns the current exchange rate between two currencies.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_currency": {
                    "type": "string",
                    "description": "Base currency, e.g., EUR"
                },
                "to_currency": {
                    "type": "string",
                    "description": "Target currency, e.g., USD"
                }
            },
            "required": ["from_currency", "to_currency"]
        }
    }
]

# ========== 3. Utility: Ticker search ==========
@st.cache_data(ttl=600)
def find_ticker(query):
    """
    Tries to find the corresponding ticker symbol for a company name or synonym.
    """
    try:
        data = yf.Ticker(query)
        if data.info and "symbol" in data.info:
            return data.info["symbol"]
        tickers = yf.utils.get_tickers(query)
        if tickers:
            return tickers[0]
    except Exception:
        pass
    return query  # Fallback: use input directly

# ========== 4. Stock price query & chart (yfinance) ==========
def get_stock_price(ticker_or_name):
    ticker = find_ticker(ticker_or_name)
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d")
        if hist.empty:
            return "❌ Could not find any price data. Please check the ticker symbol or company name."
        last_quote = hist.iloc[-1]
        price = round(last_quote["Close"], 2)
        high = round(last_quote["High"], 2)
        low = round(last_quote["Low"], 2)
        volume = int(last_quote["Volume"])
        last_date = hist.index[-1].strftime("%d.%m.%Y")
        name = stock.info.get("shortName", ticker)
        return (f"**{name} ({ticker}) as of {last_date}**\n"
                f"Closing price: **{price} USD**\n"
                f"High: {high} USD, Low: {low} USD, Volume: {volume}\n\n"
                f"_Source: Yahoo Finance (yfinance), as of {last_date}_")
    except Exception as e:
        return f"❌ Error while retrieving stock data: {str(e)}. Please contact support: {SUPPORT_PHONE_NUMBER}"

def get_stock_history(ticker_or_name):
    ticker = find_ticker(ticker_or_name)
    stock = yf.Ticker(ticker)
    hist = stock.history(period="7d")
    if hist.empty:
        return "❌ No stock data available for this company."
    hist = hist.tail(7)
    md = f"Here is the price history for {stock.info.get('shortName', ticker)} ({ticker}) for the last seven days:\n\n"
    md += "\n".join(
        [f"* **{d.strftime('%d.%m.%Y')}: {c:.2f} USD**" for d, c in zip(hist.index[::-1], hist['Close'][::-1])]
    )
    return md

def plot_stock_history(ticker_or_name):
    ticker = find_ticker(ticker_or_name)
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d")
        if hist.empty:
            st.warning("No price data available.")
            return
        fig, ax = plt.subplots()
        hist["Close"].plot(ax=ax, marker="o", title=f"{ticker} – Closing Price (last 7 days)")
        ax.set_ylabel("Price in USD")
        st.pyplot(fig)
    except Exception:
        st.error("Error while creating the chart.")

# ========== 5. News via NewsAPI.org ==========
@st.cache_data(ttl=120)
def get_financial_news(ticker_or_name):
    try:
        company = yf.Ticker(find_ticker(ticker_or_name))
        name = company.info.get("shortName", ticker_or_name)
    except Exception:
        name = ticker_or_name
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={name}&"
        f"language=en&"
        f"sortBy=publishedAt&"
        f"pageSize=5&"
        f"apiKey={NEWSAPI_KEY}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        return f"❌ Error while retrieving news (Status {response.status_code})."
    news = response.json().get("articles", [])
    if not news:
        return f"ℹ️ No recent news found for **{name}**."
    result = ""
    for n in news:
        published = n.get("publishedAt", "")
        try:
            published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            published_str = published_dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            published_str = published[:10]
        title = n.get("title", "No title")
        link = n.get("url", "")
        source = n.get("source", {}).get("name", "")
        result += f"- {published_str} ({source}): [{title}]({link})\n"
    result += f"\n_Source: newsapi.org, as of {datetime.now().strftime('%d.%m.%Y %H:%M')}_"
    return result

# ========== 6. Exchange rates via Open Exchange Rates ==========
@st.cache_data(ttl=300)
def get_exchange_rate(from_currency, to_currency):
    url = (
        f"https://openexchangerates.org/api/latest.json?"
        f"app_id={OPENEXCHANGE_API_KEY}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        return f"❌ Error while retrieving exchange rate (Status {response.status_code})."
    data = response.json()
    rates = data.get("rates", {})
    try:
        rate_from = rates[from_currency.upper()]
        rate_to = rates[to_currency.upper()]
        exchange_rate = round(rate_to / rate_from, 4)
        timestamp = datetime.utcfromtimestamp(data.get("timestamp", 0)).strftime("%d.%m.%Y %H:%M")
        return (f"1 {from_currency.upper()} = **{exchange_rate} {to_currency.upper()}**\n"
                f"_Source: Open Exchange Rates, as of {timestamp} UTC_")
    except Exception:
        return "❌ The currency pair could not be found."

# ========== 7. Session state & download function ==========
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "system",
        "content": (
            "You are a helpful financial assistant. "
            "Only answer questions about stocks, markets, financial data, financial news, and exchange rates. "
            "For all other topics, politely explain that you can only answer financial questions. "
            "If users ask about current stock prices, price histories, or market data, use get_stock_price or get_stock_history. "
            "For company news, use get_financial_news. "
            "For currency and exchange rates, use get_exchange_rate. "
            "For all other topics, DO NOT answer, but inform users that you are only responsible for finance and market inquiries. "
            "If data is missing, kindly refer users to the support hotline 070-1234-5678."
        )
    })

def download_chat_history():
    output = StringIO()
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            output.write(f"User: {msg['content']}\n")
        elif msg["role"] == "assistant":
            output.write(f"Assistant: {msg['content']}\n")
    return output.getvalue().encode("utf-8")

# ========== 8. Streamlit UI ==========
st.title("📈 Stock and Finance Chatbot")
st.write(
    "Ask questions about stock prices, price histories, financial news, or exchange rates. "
    "For support: **070-1234-5678**"
)

st.markdown("**Example queries:**")
st.markdown("""
- What is the current price of Apple stock?
- Show me the price history for Tesla.
- What’s new with SAP?
- What is the exchange rate from EUR to USD?
""")

user_input = st.text_input("🗨️ Enter your question here:")

# Download button for chat history (optional, after more than 2 messages)
if len(st.session_state.messages) > 2:
    st.download_button(
        label="💾 Download chat history",
        data=download_chat_history(),
        file_name="financechat_history.txt"
    )

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.spinner("Generating response..."):
        response = client.chat.completions.create(
            model=model,
            messages=st.session_state.messages,
            functions=functions,
            function_call="auto"
        )
        response_message = response.choices[0].message

        if response_message.function_call:
            function_name = response_message.function_call.name
            arguments = json.loads(response_message.function_call.arguments)
            function_response = ""
            if function_name == "get_stock_price":
                ticker = arguments.get("ticker")
                function_response = get_stock_price(ticker)
            elif function_name == "get_stock_history":
                ticker = arguments.get("ticker")
                function_response = get_stock_history(ticker)
            elif function_name == "get_financial_news":
                ticker = arguments.get("ticker")
                function_response = get_financial_news(ticker)
            elif function_name == "get_exchange_rate":
                from_curr = arguments.get("from_currency")
                to_curr = arguments.get("to_currency")
                function_response = get_exchange_rate(from_curr, to_curr)
            else:
                function_response = "Unknown function call."

            st.session_state.messages.append({
                "role": "function",
                "name": function_name,
                "content": function_response
            })

            # GPT responds again – now with the function response
            second_response = client.chat.completions.create(
                model=model,
                messages=st.session_state.messages,
            )
            final_message = second_response.choices[0].message.content
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_message
            })

            # IMPORTANT: Only plot price history on success
            if function_name == "get_stock_history":
                if not function_response.startswith("❌"):
                    plot_stock_history(arguments.get("ticker"))
                else:
                    st.warning(function_response)
            elif function_name == "get_stock_price":
                # Optionally: show price chart here as well
                pass
            elif function_name == "get_financial_news":
                if "Error" in function_response or "no recent news" in function_response.lower():
                    st.warning(function_response)
            elif function_name == "get_exchange_rate":
                if "Error" in function_response or "not found" in function_response:
                    st.error(function_response)

            st.success(final_message)

        else:
            final_message = response_message.content
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_message
            })
            st.success(final_message)

# Visually display the chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(
            f"<div style='background-color:#eef3fc;padding:8px;border-radius:8px;color:#222222'><b>🧑 You:</b> {message['content']}</div>",
            unsafe_allow_html=True
        )
    elif message["role"] == "assistant":
        st.markdown(
            f"<div style='background-color:#e8faee;padding:8px;border-radius:8px;color:#183b1e'><b>🤖 Assistant:</b> {message['content']}</div>",
            unsafe_allow_html=True
        )

# ======= End =======
