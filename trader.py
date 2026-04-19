import json
import math
from typing import Dict, List, Any
from datamodel import TradingState, OrderDepth, Order

class Trader:
    def __init__(self):
        self.POSITION_LIMITS = {
            "ASH_COATED_OSMIUM": 80,
            "INTARIAN_PEPPER_ROOT": 80
        }
        
        self.pepper_window = 40
        self.alpha = 2 / (self.pepper_window + 1)

    def bid(self) -> int:
        # Playing it extremely safe. 
        # If we print ~500 profit, a bid of 50 secures flow without eating our lunch.
        return 50 

    def compute_vwap(self, order_depth) -> float:
        total_vol = 0
        total_value = 0
        for price, vol in order_depth.buy_orders.items():
            total_vol += abs(vol)
            total_value += price * abs(vol)
        for price, vol in order_depth.sell_orders.items():
            total_vol += abs(vol)
            total_value += price * abs(vol)
        if total_vol == 0: return 0
        return total_value / total_vol

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        
        trader_state = {"pepper_history": [], "pepper_ema": None}
        if state.traderData:
            try: trader_state = json.loads(state.traderData)
            except: pass
                
        pepper_history = trader_state.get("pepper_history", [])
        pepper_ema = trader_state.get("pepper_ema", None)

        # =====================================================================
        # 1. ASH_COATED_OSMIUM: Inventory-Skewed Market Making (Stable & Profitable)
        # =====================================================================
        osmium = "ASH_COATED_OSMIUM"
        if osmium in state.order_depths:
            order_depth = state.order_depths[osmium]
            orders: List[Order] = []
            
            if len(order_depth.sell_orders) > 0 and len(order_depth.buy_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_bid = max(order_depth.buy_orders.keys())
                mid_price = (best_ask + best_bid) / 2
                
                current_pos = state.position.get(osmium, 0)
                limit = self.POSITION_LIMITS[osmium]
                
                inventory_skew = (current_pos / limit) * 1.5 
                reservation_price = mid_price - inventory_skew
                
                my_bid = math.floor(reservation_price - 1)
                my_ask = math.ceil(reservation_price + 1)
                
                my_bid = min(my_bid, best_bid + 1)
                my_ask = max(my_ask, best_ask - 1)

                bid_vol = limit - current_pos
                ask_vol = -limit - current_pos
                
                if bid_vol > 0: orders.append(Order(osmium, my_bid, bid_vol))
                if ask_vol < 0: orders.append(Order(osmium, my_ask, ask_vol))
                    
            result[osmium] = orders

        # =====================================================================
        # 2. INTARIAN_PEPPER_ROOT: The Golden Mean Sniper
        # =====================================================================
        pepper = "INTARIAN_PEPPER_ROOT"
        if pepper in state.order_depths:
            order_depth = state.order_depths[pepper]
            orders: List[Order] = []
            
            if len(order_depth.sell_orders) > 0 and len(order_depth.buy_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_bid = max(order_depth.buy_orders.keys())
                
                vwap = self.compute_vwap(order_depth)
                if vwap == 0: vwap = (best_ask + best_bid) / 2
                
                pepper_history.append(vwap)
                if len(pepper_history) > self.pepper_window:
                    pepper_history.pop(0)
                    
                if pepper_ema is None: pepper_ema = vwap
                else: pepper_ema = (vwap * self.alpha) + (pepper_ema * (1 - self.alpha))
                
                if len(pepper_history) >= 2:
                    mean = sum(pepper_history) / len(pepper_history)
                    variance = sum((x - mean) ** 2 for x in pepper_history) / len(pepper_history)
                    std_dev = math.sqrt(variance)
                    
                    if std_dev > 0:
                        z_score = (vwap - pepper_ema) / std_dev
                        
                        current_pos = state.position.get(pepper, 0)
                        limit = self.POSITION_LIMITS[pepper]
                        
                        sniper_bid = best_bid + 1
                        sniper_ask = best_ask - 1
                        
                        if sniper_bid >= best_ask: sniper_bid = best_bid
                        if sniper_ask <= best_bid: sniper_ask = best_ask

                        # THE GOLDEN MEAN: 1.25 gives us strong conviction without starving us of trades
                        if z_score < -1.25: 
                            vol_to_buy = limit - current_pos
                            if vol_to_buy > 0:
                                orders.append(Order(pepper, sniper_bid, vol_to_buy))
                                
                        elif z_score > 1.25: 
                            vol_to_sell = -limit - current_pos 
                            if vol_to_sell < 0:
                                orders.append(Order(pepper, sniper_ask, vol_to_sell))
                                
                        # Unwinding neutral positions 
                        elif current_pos > 0 and z_score > 0:
                            orders.append(Order(pepper, sniper_ask, -current_pos)) 
                        elif current_pos < 0 and z_score < 0:
                            orders.append(Order(pepper, sniper_bid, abs(current_pos))) 

            result[pepper] = orders

        # --- State Serialization ---
        trader_state["pepper_history"] = pepper_history
        trader_state["pepper_ema"] = pepper_ema
        next_trader_data = json.dumps(trader_state)

        return result, conversions, next_trader_data