import csv
import json
from collections import defaultdict
from datamodel import TradingState, OrderDepth, Listing
from trader import Trader

def run_local_simulation(csv_filepath):
    print(f"--- Starting Round 2 PnL Simulation for {csv_filepath} ---")
    trader = Trader()
    trader_data = ""
    
    positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    cash = 0.0
    
    market_data = defaultdict(dict)
    mid_prices = defaultdict(dict) 
    
    with open(csv_filepath, 'r') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            ts = int(row['timestamp'])
            product = row['product']
            
            depth = OrderDepth()
            for i in range(1, 4):
                if row.get(f'bid_price_{i}') and row.get(f'bid_volume_{i}'):
                    depth.buy_orders[int(row[f'bid_price_{i}'])] = int(row[f'bid_volume_{i}'])
            for i in range(1, 4):
                if row.get(f'ask_price_{i}') and row.get(f'ask_volume_{i}'):
                    depth.sell_orders[int(row[f'ask_price_{i}'])] = -abs(int(row[f'ask_volume_{i}']))
            
            market_data[ts][product] = depth
            mid_prices[ts][product] = float(row['mid_price'])

    timestamps = sorted(market_data.keys())
    
    for ts in timestamps:
        state = TradingState(
            traderData=trader_data,
            timestamp=ts,
            listings={"ASH_COATED_OSMIUM": Listing("ASH_COATED_OSMIUM", "ASH_COATED_OSMIUM", "XIRECS"),
                      "INTARIAN_PEPPER_ROOT": Listing("INTARIAN_PEPPER_ROOT", "INTARIAN_PEPPER_ROOT", "XIRECS")},
            order_depths=market_data[ts],
            own_trades={}, market_trades={},
            position=positions.copy(),
            observations={}
        )
        
        try:
            orders, conversions, next_trader_data = trader.run(state)
        except Exception as e:
            print(f"CRASH at Timestamp {ts}: {e}")
            break
            
        if orders:
            for symbol, order_list in orders.items():
                for o in order_list:
                    positions[symbol] += o.quantity
                    cash -= (o.price * o.quantity)
        
        trader_data = next_trader_data
        
        if ts > 0 and ts % 50000 == 0:
            portfolio_value = cash
            for symbol, pos in positions.items():
                portfolio_value += pos * mid_prices[ts].get(symbol, 0)
            
            print(f"[{ts}] PnL: {portfolio_value:.2f} XIRECS | Pos: {positions}")

    # Final calculations
    final_ts = timestamps[-1]
    final_pnl = cash
    for symbol, pos in positions.items():
        final_pnl += pos * mid_prices[final_ts].get(symbol, 0)
        
    print(f"\n=========================================")
    print(f"--- END OF DAY SIMULATION ---")
    print(f"Final Estimated PnL: {final_pnl:.2f} XIRECS")
    print(f"Ending Positions:    {positions}")
    print(f"Your MAF Bid:        {trader.bid()} XIRECS")
    print(f"=========================================\n")

if __name__ == "__main__":
    # Ensure your data folder has these files
    run_local_simulation("data/prices_round_2_day_0.csv")
    # run_local_simulation("data/prices_round_2_day_1.csv")
    # run_local_simulation("data/prices_round_2_day_-1.csv")