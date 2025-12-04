#CEX Arbitrage Trading bot

#note that this is probs not gonna work out due to gas fees per trade and that my trading capital must be high enough to be worthwhile which might be too risk, hence use this as a trading opportunity

#consider funding account with ETH or BTC and use their blockchain?? or maybe even solana depending on the lowest gas fees, use uniswap to access token like chainlink and take advantage of arbitrage trading opportunities.
import os
import time
import requests
import json
from dotenv import load_dotenv, dotenv_values

load_dotenv()
API_KEY = os.getenv("CRYPTO_API_KEY")

print("API_KEY:", API_KEY)

BASE_URL = "https://api.freecryptoapi.com/v1"

starting_BTC = 1.0



def fetch_symbol_data(symbol: str):
    url = f"{BASE_URL}/getData"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    params = {
        "symbol": symbol #e.g "BTC", "ETH"
    }
    try:
        resp = requests.get(url, headers=headers, params=params)
        print(f"Status: {resp.status_code}")
        print(f"URL: {resp.url}")
        print(f"Text: {resp.text}\n")

        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Network/HTTP error {symbol}: {e}")
        return None
    
    #Basic sanity checks on JSON content
    if data.get("status") != "success":
        print(f"API reported failure: {data}")
        return None
    
    symbols = data.get("symbols", [])
    if not symbols:
        print(f"No symbol data returneed for {symbol}")
        return None
    
    return symbols[0]

# btc_row = fetch_symbol_data("BTC")
# print("BTC row:", btc_row)




def fetch_crypto_pairs():
    gas_fees = 0.001  # 0.1% for now

    btc_row = fetch_symbol_data("BTC")
    eth_row = fetch_symbol_data("ETH")

    if btc_row is None or eth_row is None:
        print("Failed to fetch BTC or ETH data, skipping this cycle.")
        return None

    btc_last = float(btc_row["last"])
    eth_last = float(eth_row["last"])

    # For learning: assume USDT ~ USD, so BTC/USDT ~ btc_last, ETH/USDT ~ eth_last
    # And synthesize ETH/BTC from those:
    eth_btc_last = eth_last / btc_last 

    # Fake a small spread around the last price (0.05% on each side)
    spread = 0.0005

    btc_usdt = {
        "bid": btc_last * (1 - spread),
        "ask": btc_last * (1 + spread),
    }
    eth_usdt = {
        "bid": eth_last * (1 - spread),
        "ask": eth_last * (1 + spread),
    }
    eth_btc = {
        "bid": eth_btc_last * (1 - spread),
        "ask": eth_btc_last * (1 + spread),
    }


    return btc_usdt, eth_usdt, eth_btc, gas_fees

def triangle_calculations(starting_BTC, btc_usdt, eth_usdt, eth_btc, gas_fees):
    stats = {}
    #Leg 1: SELLING BTC -> BUY USDT, using BTC/USDT bid
    usdt_after_trade1 = starting_BTC * btc_usdt["bid"] * (1 - gas_fees) #units: USDT

    #Leg 2: SELLING USDT -> BUY ETH, using ETH/USDT ask
    eth_after_trade2 = usdt_after_trade1 / eth_usdt["ask"] * (1 - gas_fees) #units: ETH

    #Leg 3: SELLING ETH -> BUY BTC, using ETH/BTC bid
    btc_after_trade3 = eth_after_trade2 * eth_btc["bid"] * (1 - gas_fees) #units: BTC

    net_pnl = btc_after_trade3 - starting_BTC
    # print(f"Net profit/loss: {net_pnl}")
    pnl_percentage = (btc_after_trade3/starting_BTC - 1) * 100
    # print(f"Profit/Loss percentage: {pnl_percentage}")

    stats["final_btc"] = btc_after_trade3
    stats["net_pnl"] = net_pnl
    stats["pnl_percentage"] = pnl_percentage

    return stats 

def triangle_calculations_reverse(starting_BTC, btc_usdt, eth_usdt, eth_btc, gas_fees):
    stats = {}
    
    #Leg 1: SELLING BTC -> buy ETH, using ETH/BTC ask
    eth_after_trade1 = starting_BTC / eth_btc["ask"] * (1 - gas_fees) #units: ETH

    #Leg 2: SELLING ETH -> buy USDT, using ETH/USDT bid
    usdt_after_trade2 = eth_after_trade1 * eth_usdt["bid"] * (1 - gas_fees) #units: USDT

    #Leg 3: SELLING USDT -> buy BTC, using BTC/USDT ask
    btc_after_trade3 = usdt_after_trade2 / btc_usdt["ask"] * (1 - gas_fees) #units: BTC

    net_pnl = btc_after_trade3 - starting_BTC
    pnl_percentage = (btc_after_trade3/starting_BTC - 1) * 100

    stats["final_btc"] = btc_after_trade3
    stats["net_pnl"] = net_pnl
    stats["pnl_percentage"] = pnl_percentage

    return stats

def check_triangle(stats):
    #Trade is profitable
    if stats["net_pnl"] > 0 and stats["pnl_percentage"] > 0.5 :
        is_profitable = True

    #Trade unprofitable or margin too low and slippage might erode profits
    else: 
         is_profitable = False

    return is_profitable


def print_triangle(stats):
    print(f'Final BTC: {stats["final_btc"]:.7f}')
    print(f'Net Profit/Loss (in BTC): {stats["net_pnl"]:.7f}')
    print(f'Percentage Proft/Loss: {stats["pnl_percentage"]:.7f}%')


def main():
    while True:
        result = fetch_crypto_pairs()
        if result is None:
            time.sleep(1)
            continue

        btc_usdt, eth_usdt, eth_btc, gas_fees = result

        stats1 = triangle_calculations(starting_BTC, btc_usdt, eth_usdt, eth_btc, gas_fees)
        stats2 = triangle_calculations_reverse(starting_BTC, btc_usdt, eth_usdt, eth_btc, gas_fees)
        stats1_is_profitable = check_triangle(stats1)
        stats2_is_profitable = check_triangle(stats2)

        if stats1["net_pnl"] > stats2["net_pnl"]:
            print("\nBest direction: BTC > USDT > ETH > BTC\n")
            if stats1_is_profitable is True and stats1["pnl_percentage"] >= 0.5:
                print_triangle(stats1)
                #Execute trade
            else:
                print_triangle(stats1)
                print("\nNot profitable, skipping this triangle...")
                if 0 <= stats1["pnl_percentage"] < 0.5:
                    print("Profit margin too small, slippage erodes profit..")
                elif stats1["pnl_percentage"] < 0:
                    print("Negative profits")

        elif stats1["net_pnl"] < stats2["net_pnl"]:
            print("\nBest direction: BTC > ETH > USDT > BTC\n")
            if stats2_is_profitable is True and stats2["pnl_percentage"] >= 0.5:
                print_triangle(stats2)
                #Execute trade
            else:
                print_triangle(stats2)
                print("Not profitable, skipping this triangle...")
                if 0 <= stats2["pnl_percentage"] < 0.5:
                    print("Profit margin too small, slippage erodes profit..")
                elif stats2["pnl_percentage"] < 0:
                    print("Negative profits")

        
        prompt = input("\nDo you wish to continue(y/n): ").lower()
        
        if prompt[0] == 'y':
            continue
        elif prompt[0] == 'n':
            break
        
        time.sleep(1)


if __name__ == "__main__":
    main()





# def fetch_symbol_price(symbol: str, api_key: str) -> float | None:
#     url = "https://api.freecryptoapi.com/v1/getData"
#     headers = {
#         "Authorization": f"Bearer {api_key}"
#     }
#     params = {"symbol": symbol}

#     try:
#         resp = requests.get(url, headers=headers, params=params, timeout=10)
#         resp.raise_for_status()
#         data = resp.json()

#         # TODO: replace 'price' with the actual key path you saw
#         price = data["price"]
#         return float(price)
#     except (requests.exceptions.RequestException, KeyError, TypeError, ValueError) as e:
#         print(f"Error fetching price for {symbol}: {e}")
#         return None





# def get_symbol_data(symbol: str):
#     url = f"{BASE_URL}/getData"
#     headers = {
#         "Authorization": f"Bearer {API_KEY}",
#     }
#     params = {
#         "symbol": symbol,   # e.g. "BTC", "ETH"
#     }

#     resp = requests.get(url, headers=headers, params=params)
#     print("Status:", resp.status_code)
#     print("URL:", resp.url)
#     print("Text:", resp.text[:500])  # preview first 500 chars

#     resp.raise_for_status()
#     return resp.json()

# data_btc = get_symbol_data("BTC")
# print("Parsed JSON:", data_btc)