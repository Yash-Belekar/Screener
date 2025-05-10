import requests




def get_top_movers(limit=3):
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "linear"}  # USDT perpetuals

    response = requests.get(url, params=params)
    data = response.json()

    if data["retCode"] != 0:
        raise Exception(f"API Error: {data['retMsg']}")

    tickers = data["result"]["list"]

    movers = []
    for t in tickers:
        symbol = t["symbol"]
        pct_change = float(t["price24hPcnt"]) * 100  # Convert to %
        movers.append((symbol, pct_change))

    # Sort by percentage change
    sorted_movers = sorted(movers, key=lambda x: x[1], reverse=True)
    top_gainers = sorted_movers[:limit]
    top_losers = sorted_movers[-limit:]  # already sorted ascending at bottom

    return top_gainers, top_losers

# Run it
gainers, losers = get_top_movers()
print("Top Gainers:")
for sym, pct in gainers:
    print(f"{sym}: {pct:.2f}%")

print("\nTop Losers:")
for sym, pct in losers:
    print(f"{sym}: {pct:.2f}%")
