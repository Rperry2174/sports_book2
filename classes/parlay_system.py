import numpy as np
import pandas as pd
from pulp import *
import statistics
import scipy.optimize as optimize
import operator

from .parlay import Parlay


class ParlaySystem:
    """Create ParlaySystem class to create all combinations of parlay events

    :param binaries: 2d-Array of binaries containing moneylines [[ml_a, ml_b], [ml_c, ml_d]]
    :param target_profit: Goal profit amount
    :param bounds: Tuple of bounds if minimum bet is $1.00 and max is $15.00 then (1, 15)
    """
    def __init__(self, binaries, target_profit, bounds, profit_boost_parlay=-1, profit_boost_multiplier=1, extra_parlays=[]):
        self.binaries = binaries
        self.all_parlays = []
        self.extra_parlays = extra_parlays
        self.target_profit = target_profit
        self.bounds = bounds
        
        self.profit_boost_parlay = profit_boost_parlay
        self.profit_boost_multiplier = profit_boost_multiplier


        self.create_parlay_system()

    def create_parlay_system(self):
        binary_iterations = list(itertools.product(*self.binaries))

        # NOTE: 
        # np.shape(binary_iterations) = (8, 3)

        for i, parlay in enumerate(binary_iterations):
            if i == self.profit_boost_parlay:
                current_parlay = Parlay(money_line_arr=parlay, bet_amount=100)
                current_parlay.update_money_line_odds(new_money_line_odds=(current_parlay.money_line_odds * self.profit_boost_multiplier))
            else:
                current_parlay = Parlay(money_line_arr=parlay, bet_amount=100)


            self.all_parlays.append(current_parlay)

        self.all_parlays = sorted(self.all_parlays, key=operator.attrgetter('implied_prob'))

    def slsqp_solver(self, profit_type):
        def avg_profit(x):   # The rosenbrock function
            parlay_profits = []

            for i in range(len(x)):
                if i > len(self.all_parlays) - 1 and len(self.extra_parlays) > 0:
                    parlay = self.extra_parlays[i - len(self.all_parlays) - 1 ]
                else:
                    parlay = self.all_parlays[i]

                # parlay = self.all_parlays[i]
                parlay.update_bet_amount(x[i])
                profit = parlay.payout - sum(x)
                parlay_profits.append(profit)

            # print("statistics.mean(parlay_profits): ", statistics.mean(parlay_profits))
            return -statistics.mean(parlay_profits)

        def avg_implied_profit(x):
            print(f'looiking at x: {x}')
            parlay_profits = []

            for i in range(len(x)):
                if i > len(self.all_parlays) - 1 and len(self.extra_parlays) > 0:
                    parlay = self.extra_parlays[i - len(self.all_parlays) - 1 ]
                else:
                    parlay = self.all_parlays[i]
                # parlay = self.all_parlays[i]
                parlay.update_bet_amount(x[i])
                # profit = (parlay.payout * parlay.implied_prob) - sum(x)
                profit = parlay.payout - sum(x)
                profit *= parlay.implied_prob

                parlay_profits.append(profit)

            # print("statistics.mean(parlay_profits): ", statistics.mean(parlay_profits))
            return -statistics.mean(parlay_profits)

        bnds = ()
        for i in range(len(self.all_parlays)):
            bnds += (self.bounds,)
        for i in range(len(self.extra_parlays)):
            # Todo: Add extra parlays specific bounds
            bnds += (self.bounds,)

        # cons = [{'type': 'ineq', 'fun': lambda x, i=i : x[i] * self.all_parlays[i].decimal_odds - self.target_profit - sum(x) } for i in range(len(self.all_parlays))]

        cons = []
        for i in range(len(self.all_parlays)):
            cons.append({'type': 'ineq', 'fun': lambda x, i=i : x[i] * self.all_parlays[i].decimal_odds - self.target_profit - sum(x) })
        
        for i in range(len(self.extra_parlays)):
            cons.append({'type': 'ineq', 'fun': lambda x, i=i : x[i] * self.extra_parlays[i].decimal_odds - self.target_profit - sum(x) })


        print(f'''
            constraints:
            {cons}

            bounds:
            {bnds}
        ''')
        # COBYLA doesn't support bounds in this format
        # implied_prob_arr = np.array([par.implied_prob for par in self.all_parlays])

        if profit_type == 'avg_profit':
            final_val = optimize.minimize(avg_profit, np.ones(len(self.all_parlays) + len(self.extra_parlays)), method='SLSQP', bounds=bnds, constraints=cons)
        elif profit_type == 'avg_implied_profit':
            final_val = optimize.minimize(avg_implied_profit, np.ones(len(self.all_parlays) + len(self.extra_parlays)), method='SLSQP', bounds=bnds, constraints=cons)

        print(f'''
            final_val:
            {final_val}
        ''')

        events_arr = []
        decimal_odds_arr = []
        money_line_odds_arr = []
        bets_arr = []
        payouts_arr = []
        profits_arr = []
        implied_prob_arr = []
        overrides_arr = []

        for i in range(len(final_val.x)):
            solver_bet_amount = final_val.x[i]

            if i > len(self.all_parlays) - 1 and len(self.extra_parlays) > 0:
                parlay = self.extra_parlays[i - len(self.all_parlays) - 1 ]
            else:
                parlay = self.all_parlays[i]



            # parlay = self.all_parlays[i]



            parlay.update_bet_amount(solver_bet_amount)
            profit = solver_bet_amount * parlay.decimal_odds - sum(final_val.x)

            events_arr.append(parlay.event)
            bets_arr.append(round(solver_bet_amount, 4))
            decimal_odds_arr.append(round(parlay.decimal_odds, 4))
            money_line_odds_arr.append(parlay.money_line_odds)
            implied_prob_arr.append(parlay.implied_prob)
            payouts_arr.append(round(parlay.payout, 4))
            overrides_arr.append(1 if parlay.overrides['money_line_odds'] else 0)

            profits_arr.append(round(profit, 3))

        print(f'''
            {events_arr}
            {money_line_odds_arr}
            {bets_arr}
            {decimal_odds_arr}
            {implied_prob_arr}
            {payouts_arr}
            {overrides_arr}
            {profits_arr}
        ''')

        df = pd.DataFrame({'event': events_arr,
                           'ml_odds': money_line_odds_arr,
                           'dec_odds': decimal_odds_arr,
                           'bet': bets_arr,
                           'implied_prob': implied_prob_arr,
                           'payout': payouts_arr,
                           'override': overrides_arr,
                           'profit': profits_arr
                            })

        df = df.sort_values(by=['profit'], ascending=[False])
        total_bet = round(sum(bets_arr), 2)

        print(f'''
            Parlay system total bet {total_bet}:
        ''')

        return df
