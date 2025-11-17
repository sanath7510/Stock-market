
import yfinance as yf
import matplotlib.pyplot as plt
from StockPrediction import profit_margin_fuzz, debt_ratio_fuzz, roa_fuzz, price_var_fuzz, ctrl
import numpy as np

def get_financial_ratios(ticker):
    stock = yf.Ticker(ticker)

    # Get financial data
    fin = stock.financials
    bs = stock.balance_sheet

    # Profit Margin = Net Income / Total Revenue * 100
    net_income = fin.loc["Net Income"].iloc[0]
    total_revenue = fin.loc["Total Revenue"].iloc[0]
    profit_margin = (net_income / total_revenue) * 100

    # Debt Ratio = Total Liabilities / Total Assets * 100
    total_liabilities = bs.loc["Total Liabilities"].iloc[0]
    total_assets = bs.loc["Total Assets"].iloc[0]
    debt_ratio = (total_liabilities / total_assets) * 100

    # ROA = Net Income / Total Assets * 100
    roa = (net_income / total_assets) * 100

    return profit_margin, debt_ratio, roa

def predict_price_change(pm, dr, roa):
    # Create control system
    system_ctrl = ctrl.ControlSystemSimulation(ctrl.ControlSystem(
        [rule for rule in price_var_fuzz.terms.values() if rule]  # Not actually correct but placeholder
    ))
    system_ctrl.input['Profit Margin'] = pm
    system_ctrl.input['Debt Ratio'] = dr
    system_ctrl.input['ROA'] = roa
    system_ctrl.compute()
    return system_ctrl.output['PRICE VAR [%]']

def main():
    ticker = input("Enter stock ticker (e.g., AAPL): ").upper()
    period = input("Enter time range (e.g., 1y, 6mo, 5y, max): ")

    # Get ratios
    pm, dr, roa = get_financial_ratios(ticker)

    # Predict
    predicted_change = predict_price_change(pm, dr, roa)
    print(f"Predicted Price Change: {predicted_change:.2f}%")

    # Get historical data
    hist = yf.download(ticker, period=period)
    plt.figure(figsize=(10,6))
    plt.plot(hist.index, hist['Close'], label="Historical Close Price")
    future_price = hist['Close'][-1] * (1 + predicted_change / 100)
    plt.axhline(y=future_price, color='r', linestyle='--', label=f"Predicted Future Price: {future_price:.2f}")

    plt.title(f"{ticker} Price History and Prediction")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")
    plt.legend()
    plt.show()

if __name__ == "__main__":
    main()
