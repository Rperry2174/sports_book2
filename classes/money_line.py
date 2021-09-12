import pandas as pd
from fractions import Fraction

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class MoneyLine:
    def __init__(self, event, bet_amount, money_line_odds, description=''):
        """Create moneyline class with starting parameters / initialize attributes

        :param event: Name of event (i.e. team or player the moneyline is on)
        :param bet_amount: Amount of the bet
        :param money_line_odds: +/- odds of event occurring
        :param description: description of the event occurring

        :attr decimal_odds: odds as a decimal
        :attr fractional_odds: odds as a fraction
        :attr implied_prob: implied probability of event derived from odds
        :attr payout: amount paid out if bet wins
        """
        self.index = None
        self.event = event
        self.bet_amount = bet_amount
        self.money_line_odds = money_line_odds

        # Set placeholders
        self.implied_prob = None
        self.decimal_odds = None
        self.fractional_odds = None
        self.payout = None
        self.expected_value = None

        self.overrides = {
            'implied_prob': None,
            'money_line_odds': None,
        }

        # Update payout based on decimal
        self.df_stats = self.update_statistics()

    @staticmethod
    def odds_to_decimal(money_line_odds):
        if money_line_odds > 0:
            return 1 + (money_line_odds / 100.0)
        else:
            return 1 + (100.0 / abs(money_line_odds))

    @staticmethod
    def odds_to_implied_probability(money_line_odds):
        if money_line_odds > 0:
            return 100.0 / (100.0 + money_line_odds)
        else:
            return abs(money_line_odds) / (100 + abs(money_line_odds))

    @staticmethod
    def decimal_to_fractional(decimal_odds):
        return Fraction(decimal_odds).limit_denominator(5)

    @staticmethod
    def decimal_odds_to_payout(decimal_odds, bet_amount):
        return decimal_odds * bet_amount

    @staticmethod
    def payout_to_expected_value(payout, implied_prob):
        return payout * implied_prob

    @staticmethod
    def decimal_to_money_line_odds(decimal_odds):
        # 2.0 decimal odds means +100 odds or more positive
        if decimal_odds > 2.0:
            return 100.0 * (decimal_odds - 1.0)
        else:
            # Note: idt this should ever happen in a parlay fundamentally
            return abs(100.0 / (decimal_odds - 1.0))

    def apply_percent_boost(self, pct_boost):
        if self.money_line_odds < 0:
            return self.money_line_odds / (1 + pct_boost)
        else:
            return self.money_line_odds * (1 + pct_boost)

    def update_bet_amount(self, new_bet_amount):
        self.bet_amount = new_bet_amount
        self.update_statistics()

    def update_money_line_odds(self, new_money_line_odds):
        self.overrides['money_line_odds'] = new_money_line_odds
        self.update_statistics()

    def update_implied_prob(self, new_implied_prob):
        self.overrides['implied_prob'] = new_implied_prob
        self.update_statistics()

    def handle_overrides(self):
        """Handle updating money_lineodds, decimal_odds, and implied_prob based on overrides
        """
        if self.overrides['money_line_odds']:
            self.money_line_odds = self.overrides['money_line_odds']

        self.decimal_odds = self.odds_to_decimal(money_line_odds=self.money_line_odds)

        # Handle override of implied_prob
        if self.overrides['implied_prob']:
            self.implied_prob = self.overrides['implied_prob']
        else:
            self.implied_prob = self.odds_to_implied_probability(money_line_odds=self.money_line_odds)

    def update_statistics(self):
        # Calculate all calculated attributes
        # Handle override of money_line_odds or implied_probability
        # Note: this method requires that moneyline odds have been either set or calculated before it runs
        self.handle_overrides()

        self.fractional_odds = self.decimal_to_fractional(decimal_odds=self.decimal_odds)
        self.payout = self.decimal_odds_to_payout(decimal_odds=self.decimal_odds, bet_amount=self.bet_amount)
        self.expected_value = self.payout_to_expected_value(payout=self.payout, implied_prob=self.implied_prob)

        self.df_stats = pd.DataFrame({
            'join_index': [0],
            'event': [self.event],
            'bet_amount': [self.bet_amount],
            'money_line_odds': [self.money_line_odds],
            'decimal_odds': [self.decimal_odds],
            'fractional_odds': [self.fractional_odds],
            'implied_prob': [self.implied_prob],
            'payout': [self.payout],
            'expected_value': [self.expected_value],
        })

        self.df_stats = self.df_stats.set_index(['join_index'])
        self.add_column_suffix()

        return self.df_stats

    def add_column_suffix(self):
        columns = self.df_stats.columns

        new_columns = [f'{col}_{self.event}' for col in columns]
        self.df_stats.columns = new_columns

    def print_stats(self):
        print(self.df_stats)
