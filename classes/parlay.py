import pandas as pd

from .money_line import MoneyLine

class Parlay(MoneyLine):
    def __init__(self, money_line_arr, bet_amount):
        """Create Parlay class which is subclas of moneyline and has ability to contain
        multiple moneylines

        :param money_line_arr: +/- odds of event occurring
        :param bet_amount: Amount of the bet

        (inherited) :param event: Name of event (i.e. team or player the moneyline is on)
        (inherited) :param money_line_odds: +/- odds of event occurring
        (inherited) :param description: description of the event occurring
        (inherited) :attr decimal_odds: odds as a decimal
        (inherited) :attr fractional_odds: odds as a fraction
        (inherited) :attr implied_prob: implied probability of event derived from odds
        (inherited) :attr payout: amount paid out if bet wins
        (inherited) :attr df_stats: stats about parlay as a pandas dataframe
        """

        # Inputs
        self.money_line_arr = money_line_arr
        self.bet_amount = bet_amount

        # Set base df_stats dataframe and metrics that other functions use to derive stats
        self.df_stats = self.ml_arr_to_df_stats(money_line_arr=self.money_line_arr)
        self.event = self.df_stats_to_event(df_stats=self.df_stats)
        self.decimal_odds = self.df_stats_to_decimal_odds(df_stats=self.df_stats)
        self.implied_prob = self.df_stats_to_implied_prob(df_stats=self.df_stats)
        self.money_line_odds = self.decimal_to_money_line_odds(decimal_odds=self.decimal_odds)

        self.overrides = {
            'implied_prob': None,
            'money_line_odds': None,
        }

        self.df_stats = self.update_statistics()

    @staticmethod
    def ml_arr_to_df_stats(money_line_arr):
        df_arr = [ml.df_stats for ml in money_line_arr]
        join_df = pd.concat(df_arr, axis=1, sort=False)

        df_stats = join_df.reset_index()

        return df_stats

    @staticmethod
    def df_stats_to_implied_prob(df_stats):
        def multiply_all_implied_prob(row, prefix='implied_prob'):
            filtered_row = row.filter(like=prefix, axis=0)

            base = 1
            for val in filtered_row:
                base *= val
            return base

        df_stats['implied_prob'] = df_stats.apply(lambda x: multiply_all_implied_prob(x), axis=1)
        return df_stats.loc[0, 'implied_prob']

    @staticmethod
    def df_stats_to_event(df_stats):
        def join_event_names(row, prefix='event'):
            filtered_row = row.filter(like=prefix, axis=0)

            base = '_'
            result = base.join(sorted(list(filtered_row)))
            return result

        df_stats['event_parlay'] = df_stats.apply(lambda x: join_event_names(x), axis=1)
        event = df_stats.loc[0, 'event_parlay']

        return event

    @staticmethod
    def df_stats_to_decimal_odds(df_stats):
        def multiply_all_dec_odds(row, prefix='decimal'):
            filtered_row = row.filter(like=prefix, axis=0)

            base = 1
            for val in filtered_row:
                base *= val
            return base

        df_stats['decimal_parlay'] = df_stats.apply(lambda x: multiply_all_dec_odds(x), axis=1)
        return df_stats.loc[0, 'decimal_parlay']

    # Note: This overrides the update_statistics() method from MoneyLine class
    def update_statistics(self):
        # Note: this method requires that moneyline odds have been either set or calculated before it runs
        self.handle_overrides()

        # Calculate all calculated attributes
        self.fractional_odds = self.decimal_to_fractional(decimal_odds=self.decimal_odds)
        self.payout = self.decimal_odds_to_payout(decimal_odds=self.decimal_odds, bet_amount=self.bet_amount)
        self.expected_value = self.payout_to_expected_value(payout=self.payout, implied_prob=self.implied_prob)

        self.df_stats['event_parlay'] = self.event
        self.df_stats['money_line_odds_parlay'] = self.money_line_odds
        self.df_stats['decimal_parlay'] = self.decimal_odds
        self.df_stats['implied_prob_parlay'] = self.implied_prob
        self.df_stats['fractional_odds_parlay'] = self.fractional_odds
        self.df_stats['payout_parlay'] = self.payout
        self.df_stats['expected_value_parlay'] = self.implied_prob * self.payout

        return self.df_stats


