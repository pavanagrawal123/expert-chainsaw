import numpy as np
from gym import spaces

from .trading_env import TradingEnv, Actions, Positions
from enum import Enum

class Actions(Enum):
    Sell = 1
    Flat = 0
    Buy = 2


class Positions(Enum):
    Short = 1
    Flat = 0
    Long = 2



class StocksEnv(TradingEnv):
    def __init__(self, df, window_size, frame_bound):
        assert len(frame_bound) == 2

        self.frame_bound = frame_bound
        super().__init__(df, window_size)

        self.trade_fee_bid_percent = 0.01  # unit
        self.trade_fee_ask_percent = 0.005  # unit
        self.action_space = spaces.Discrete(len(Actions))
        self.max_possible_positions = 5  # initializing the max # of active positions
        self.current_positions = 0  # track # active positions
        self.current_position_cost_bases = []  # dictionary where keys = numbers corresponding to each position index; values = array of important values (cost bases)

        #self.current_position_weights = [] # array of weights for each position in portfolio

    def _process_data(self):
        prices = self.df.loc[:, 'Close'].to_numpy()

        prices[self.frame_bound[0] - self.window_size]  # validate index (TODO: Improve validation)
        prices = prices[self.frame_bound[0]-self.window_size:self.frame_bound[1]]

        diff = np.insert(np.diff(prices), 0, 0)
        signal_features = np.column_stack((prices, diff))

        return prices, signal_features


    def _calculate_reward(self, action):
        step_reward = 0
        #action = action[0]
        trade = False
        if ((action == Actions.Buy.value and self._position == Positions.Short) or
            (action == Actions.Sell.value and self._position == Positions.Long)):
            trade = True

        if trade:
            current_price = self.prices[self._current_tick]
            last_trade_price = self.prices[self._last_trade_tick]
            price_diff = current_price - last_trade_price

            if self._position == Positions.Long:
                step_reward += price_diff

        current_price = self.prices[self._current_tick]
        if action == Actions.Buy.value or action == Actions.Sell.value:
            net_change = 1 if action == Actions.Buy.value else -1
            net_new_pos = self.current_positions + net_change
            if abs(net_new_pos) < self.max_possible_positions:
                if self.current_positions > 0 and action == Actions.Sell.value:
                    cost_basis = self.current_position_cost_bases.pop(0)
                    self.current_positions -= 1
                    self._total_profit += current_price - cost_basis
                if self.current_positions >= 0 and action == Actions.Buy.value:
                    self.current_position_cost_bases.append(current_price)
                    self.current_positions += 1
                if self.current_positions <= 0 and action == Actions.Sell.value:
                    self.current_position_cost_bases.append(-current_price)
                    self.current_positions -= 1
                if self.current_positions < 0 and action == Actions.Buy.value:
                    cost_basis = self.current_position_cost_bases.pop(0)
                    self.current_positions += 1
                    self._total_profit += cost_basis - current_price
        unrealized_pnl = current_price * self.current_positions - sum(self.current_position_cost_bases)
        return -(unrealized_pnl*unrealized_pnl) if unrealized_pnl < 0 else unrealized_pnl

    def _update_profit(self, action):
        return


        trade = False

        if ((
                action == Actions.Buy.value and self.current_positions < self.max_possible_positions)):  # if the requested trade won't exceed the portfolio max size, you can trade
            trade = True
            self.current_positions += 1

        if ((action == Actions.Buy.value and self._position == Positions.Short) or
                (action == Actions.Sell.value and self._position == Positions.Long)):
            trade = True

        if trade or self._done:
            # find value of current positions
            self.current_position_weights / np.sum(
                self.current_position_weights)  # normalizing position weights to sum to 1

            current_price = self.prices[self._current_tick]
            last_trade_price = self.prices[self._last_trade_tick]

            if self._position == Positions.Long:
                shares = (self._total_profit * (1 - self.trade_fee_ask_percent)) / last_trade_price



    def max_possible_profit(self):
        current_tick = self._start_tick
        last_trade_tick = current_tick - 1
        profit = 1.

        while current_tick <= self._end_tick:
            position = None
            if self.prices[current_tick] < self.prices[current_tick - 1]:
                while (current_tick <= self._end_tick and
                       self.prices[current_tick] < self.prices[current_tick - 1]):
                    current_tick += 1
                position = Positions.Short
            else:
                while (current_tick <= self._end_tick and
                       self.prices[current_tick] >= self.prices[current_tick - 1]):
                    current_tick += 1
                position = Positions.Long

            if position == Positions.Long:
                current_price = self.prices[current_tick - 1]
                last_trade_price = self.prices[last_trade_tick]
                shares = profit / last_trade_price
                profit = shares * current_price
            last_trade_tick = current_tick - 1

        return profit
