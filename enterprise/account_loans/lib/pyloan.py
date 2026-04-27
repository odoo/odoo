"""
Taken from https://github.com/sudo-dakix/pyloan

MIT License

Copyright (c) 2021 Da.Ki.X

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Disable Ruff as we simply import the code from pyloan without any modifications
# ruff: noqa

import datetime as dt
import calendar as cal
import collections
from decimal import Decimal
from dateutil.relativedelta import relativedelta

Payment = collections.namedtuple('Payment',
                                 ['date', 'payment_amount', 'interest_amount', 'principal_amount',
                                  'special_principal_amount', 'total_principal_amount',
                                  'loan_balance_amount'])

Special_Payment = collections.namedtuple('Special_Payment', ['payment_amount', 'first_payment_date',
                                                             'special_payment_term',
                                                             'annual_payments'])
Loan_Summary = collections.namedtuple('Loan_Summary', ['loan_amount', 'total_payment_amount',
                                                       'total_principal_amount',
                                                       'total_interest_amount',
                                                       'residual_loan_balance',
                                                       'repayment_to_principal'])


class Loan(object):

    def __init__(self, loan_amount, interest_rate, loan_term, start_date, payment_amount=None,
                 first_payment_date=None, payment_end_of_month=True, annual_payments=12,
                 interest_only_period=0, compounding_method='30E/360', loan_type='annuity'):

        '''
        Input validtion for attribute loan_amount
        '''
        try:
            if isinstance(loan_amount, int) or isinstance(loan_amount, float):
                if loan_amount < 0:
                    raise ValueError('Variable LOAN_AMMOUNT can only be non-negative.')
            else:
                raise TypeError(
                    'Variable LOAN_AMOUNT can only be of type integer or float, both non-negative.')

        # handle exceptions for loan_amount
        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)

        else:
            self.loan_amount = Decimal(str(loan_amount))

        '''
        Input validation for attribute interet_rate
        '''
        try:
            if isinstance(interest_rate, int) or isinstance(interest_rate, float):
                if interest_rate < 0:
                    raise ValueError('Variable INTEREST_RATE can only be non-negative.')
            else:
                raise TypeError(
                    'Variable INTEREST_RATE can only be of type integer or float, both non-negative.')

        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)

        else:
            self.interest_rate = Decimal(str(interest_rate / 100)).quantize(Decimal(str(0.000000000001)))

        '''
        Input validation for attribute loan_term
        '''
        try:
            if isinstance(loan_term, int):
                if loan_term < 1:
                    raise ValueError(
                        'Variable LOAN_TERM can only be integers greater or equal to 1.')
            else:
                raise TypeError('Variable LOAN_TERM can only be of type integer.')

        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)

        else:
            self.loan_term = loan_term

        '''
        Input validation for attribute payment_amount
        '''
        try:
            if payment_amount is None:
                pass
            elif payment_amount is not None and (
                    isinstance(payment_amount, int) or isinstance(payment_amount, float)):
                if payment_amount < 0:
                    raise ValueError('Variable PAYMENT_AMOUNT can only be non-negative.')
            else:
                raise TypeError(
                    'Variable PAYMENT_AMOUNT can only be of type integer or float, both non-negative.')

        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)

        else:
            self.payment_amount = payment_amount

        '''
        Input validation for attribute start_date
        '''
        try:
            if start_date is None:
                raise TypeError('Varable START_DATE must by of type date with format YYYY-MM-DD')
            elif bool(dt.datetime.strptime(start_date, '%Y-%m-%d')) is False:
                raise ValueError
        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)
        else:
            self.start_date = dt.datetime.strptime(start_date, '%Y-%m-%d')

        '''
        Input validation for attribute first_paymnt_date
        '''
        try:
            if first_payment_date is None:
                pass
            elif bool(dt.datetime.strptime(first_payment_date, '%Y-%m-%d')) is False:
                raise ValueError

        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)
        else:
            self.first_payment_date = dt.datetime.strptime(first_payment_date,
                                                           '%Y-%m-%d') if first_payment_date is not None else None

            try:
                if self.first_payment_date is None:
                    pass
                elif self.start_date > self.first_payment_date:
                    raise ValueError('FIRST_PAYMENT_DATE cannot be before START_DATE')

            except ValueError as val_e:
                print(val_e)

        '''
        Input validation for attribute payment_end_of_month
        '''
        try:
            if not isinstance(payment_end_of_month, bool):
                raise TypeError(
                    'Variable PAYMENT_END_OF_MONTH can only be of type boolean (either True or False)')

        except TypeError as typ_e:
            print(typ_e)

        else:
            self.payment_end_of_month = payment_end_of_month

        '''
        Input validation for attribute annual_payments
        '''
        try:
            if isinstance(annual_payments, int):
                if annual_payments not in [12, 4, 2, 1]:
                    raise ValueError(
                        'Attribute ANNUAL_PAYMENTS must be either set to 12, 4, 2 or 1.')
            else:
                raise TypeError('Attribute ANNUAL_PAYMENTS must be of type integer.')

        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)
        else:
            self.annual_payments = annual_payments

        '''
        Setting of no_of_payments and delta_dt if loan_term and annual_payments are set.
        '''
        try:
            if hasattr(self, 'loan_term') is False or hasattr(self, 'annual_payments') is False:
                print(self.loan_term)
                print(self.annual_payments)
                raise ValueError(
                    'Please make sure that LOAN_TERM and/or ANNUAL_PAYMENTS were correctly defined.11')

        except ValueError as val_e:
            print(val_e)

        else:
            self.no_of_payments = self.loan_term * self.annual_payments
            self.delta_dt = Decimal(str(12 / self.annual_payments))

        '''
        Input validation for attribute interest_only_period
        '''
        try:
            if isinstance(interest_only_period, int):
                if interest_only_period < 0:
                    raise ValueError(
                        'Attribute INTEREST_ONLY_PERIOD must be greater or equal to 0.')
                elif hasattr(self, 'no_of_payments') is False:
                    raise ValueError(
                        'Please make sure that LOAN_TERM and/or ANNUAL_PAYMENTS were correctly defined.')
                elif hasattr(self,
                             'no_of_payments') is True and self.no_of_payments - interest_only_period < 0:
                    raise ValueError(
                        'Attribute INTEREST_ONLY_PERIOD is greater than product of LOAN_TERM and ANNUAL_PAYMENTS.')
            else:
                raise TypeError('Attribute INTEREST_ONLY_PERIOD must be of type integer.')

        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)
        else:
            self.interest_only_period = interest_only_period

        '''
        Input validation for attribute compounding_method
        '''
        try:
            if isinstance(compounding_method, str):
                if compounding_method not in ['30A/360', '30U/360', '30E/360', '30E/360 ISDA',
                                              'A/360', 'A/365F', 'A/A ISDA', 'A/A AFB']:
                    raise ValueError(
                        'Attribute COMPOUNDING_METHOD must be set to one of the following: 30A/360, 30U/360, 30E/360, 30E/360 ISDA, A/360, A/365F, A/A ISDA, A/A AFB.')
            else:
                raise TypeError('Attribute COMPOUNDING_METHOD must be of type string')

        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)
        else:
            self.compounding_method = compounding_method

        '''
        Input validation for attribute loan_type
        '''
        try:
            if isinstance(loan_type, str):
                if loan_type not in ['annuity', 'linear', 'interest-only']:
                    raise ValueError(
                        'Attribute LOAN_TYPE must be either set to annuity or linear or interest-only.')
            else:
                raise TypeError('Attribute LOAN_TYPE must be of type string')

        except ValueError as val_e:
            print(val_e)
        except TypeError as typ_e:
            print(typ_e)
        else:
            self.loan_type = loan_type

        # define non-input variables
        self.special_payments = []
        self.special_payments_schedule = []

    @staticmethod
    def _quantize(amount):
        return Decimal(str(amount)).quantize(Decimal(str(0.01)))

    @staticmethod
    def _get_day_count(dt1, dt2, method, eom=False):

        def get_julian_day_number(y, m, d):
            julian_day_count = (1461 * (y + 4800 + (m - 14) / 12)) / 4 + (
                        367 * (m - 2 - 12 * ((m - 14) / 12))) / 12 - (
                                           3 * ((y + 4900 + (m - 14) / 12) / 100)) / 4 + d - 32075
            return julian_day_count

        y1, m1, d1 = dt1.year, dt1.month, dt1.day
        y2, m2, d2 = dt2.year, dt2.month, dt2.day
        dt1_eom_day = cal.monthrange(y1, m1)[1]
        dt2_eom_day = cal.monthrange(y2, m2)[1]

        if method in {'30A/360', '30U/360', '30E/360', '30E/360 ISDA'}:
            if method == '30A/360':
                d1 = min(d1, 30)
                d2 = min(d2, 30) if d1 == 30 else d2
            if method == '30U/360':
                if eom and m1 == 2 and d1 == dt1_eom_day and m2 == 2 and d2 == dt2_eom_day:
                    d2 = 30
                if eom and m1 == 2 and d1 == dt1_eom_day:
                    d1 = 30
                if d2 == 31 and d1 >= 30:
                    d2 = 30
                if d1 == 31:
                    d1 = 30
            if method == '30E/360':
                if d1 == 31:
                    d1 = 30
                if d2 == 31:
                    d2 = 30
            if method == '30E/360 ISDA':
                if d1 == dt1_eom_day:
                    d1 = 30
                if d2 == dt2_eom_day and m2 != 2:
                    d2 = 30

            day_count = (360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1))
            year_days = 360

        if method == 'A/365F':
            day_count = (dt2 - dt1).days
            year_days = 365

        if method == 'A/360':
            day_count = (dt2 - dt1).days
            year_days = 360

        if method in {'A/A ISDA', 'A/A AFB'}:
            djn_dt1 = get_julian_day_number(y1, m1, d1)
            djn_dt2 = get_julian_day_number(y2, m2, d2)
            if y1 == y2:
                day_count = djn_dt2 - djn_dt1
                if method == 'A/A ISDA':
                    year_days = 366 if cal.isleap(y2) else 365
                if method == 'A/A AFB':
                    year_days = 366 if cal.isleap(y1) and (m1 < 3) else 365
            if y1 < y2:
                djn_dt1_eoy = get_julian_day_number(y1, 12, 31)
                day_count_dt1 = djn_dt1_eoy - djn_dt1
                if method == 'A/A ISDA':
                    year_days_dt1 = 366 if cal.isleap(y1) else 365
                if method == 'A/A AFB':
                    year_days_dt1 = 366 if cal.isleap(y1) and (m1 < 3) else 365

                djn_dt2_boy = get_julian_day_number(y2, 1, 1)
                day_count_dt2 = djn_dt2 - djn_dt2_boy
                if method == 'A/A ISDA':
                    year_days_dt2 = 366 if cal.isleap(y2) else 365
                if method == 'A/A AFB':
                    year_days_dt2 = 366 if cal.isleap(y2) and (m2 >= 3) else 365

                diff = y2 - y1 - 1

                day_count = (day_count_dt1 * year_days_dt2) + (day_count_dt2 * year_days_dt1) + (
                            diff * year_days_dt1 * year_days_dt2)
                year_days = year_days_dt1 * year_days_dt2

        factor = day_count / year_days
        return factor

    @staticmethod
    def _get_special_payment_schedule(self, special_payment):
        no_of_payments = special_payment.special_payment_term * special_payment.annual_payments
        annual_payments = special_payment.annual_payments
        dt0 = dt.datetime.strptime(special_payment.first_payment_date, '%Y-%m-%d')

        special_payment_amount = self._quantize(special_payment.payment_amount)
        initial_special_payment = Payment(date=dt0, payment_amount=self._quantize(0),
                                          interest_amount=self._quantize(0),
                                          principal_amount=self._quantize(0),
                                          special_principal_amount=special_payment_amount,
                                          total_principal_amount=self._quantize(0),
                                          loan_balance_amount=self._quantize(0))
        special_payment_schedule = [initial_special_payment]

        for i in range(1, no_of_payments):
            date = dt0 + relativedelta(months=i * 12 / annual_payments)
            special_payment = Payment(date=date, payment_amount=self._quantize(0),
                                      interest_amount=self._quantize(0),
                                      principal_amount=self._quantize(0),
                                      special_principal_amount=special_payment_amount,
                                      total_principal_amount=self._quantize(0),
                                      loan_balance_amount=self._quantize(0))
            special_payment_schedule.append(special_payment)

        return special_payment_schedule

    '''
    Define method that calculates payment schedule
    '''

    def get_payment_schedule(self):

        attributes = ['loan_amount', 'interest_rate', 'loan_term', 'payment_amount', 'start_date',
                      'first_payment_date', 'payment_end_of_month', 'annual_payments',
                      'no_of_payments', 'delta_dt', 'interest_only_period', 'compounding_method',
                      'special_payments', 'special_payments_schedule']
        raise_error_flag = 0
        for attribute in attributes:
            if hasattr(self, attribute) is False:
                raise_error_flag = raise_error_flag + 1

        try:
            if raise_error_flag != 0:
                raise ValueError(
                    'Necessary attributes are not well defined, please review your inputs')

        except ValueError as val_e:
            print(val_e)
        else:
            initial_payment = Payment(date=self.start_date, payment_amount=self._quantize(0),
                                      interest_amount=self._quantize(0),
                                      principal_amount=self._quantize(0),
                                      special_principal_amount=self._quantize(0),
                                      total_principal_amount=self._quantize(0),
                                      loan_balance_amount=self._quantize(self.loan_amount))
            payment_schedule = [initial_payment]
            interest_only_period = self.interest_only_period

            # take care of loan type
            if self.loan_type == 'annuity':
                if self.payment_amount is None:
                    regular_principal_payment_amount = self.loan_amount * (
                                (self.interest_rate / self.annual_payments) * (
                                    1 + (self.interest_rate / self.annual_payments)) ** (
                                (self.no_of_payments - interest_only_period))) / ((1 + (
                                self.interest_rate / self.annual_payments)) ** ((
                                self.no_of_payments - interest_only_period)) - 1)
                else:
                    regular_principal_payment_amount = self.payment_amount

            if self.loan_type == 'linear':
                if self.payment_amount is None:
                    regular_principal_payment_amount = self.loan_amount / (
                                self.no_of_payments - self.interest_only_period)
                else:
                    regular_principal_payment_amount = self.payment_amount

            if self.loan_type == 'interest-only':
                regular_principal_payment_amount = 0
                interest_only_period = self.no_of_payments

            if self.first_payment_date is None:
                if self.payment_end_of_month == True:
                    if self.start_date.day == \
                            cal.monthrange(self.start_date.year, self.start_date.month)[1]:
                        dt0 = self.start_date
                    else:
                        dt0 = dt.datetime(self.start_date.year, self.start_date.month,
                                          cal.monthrange(self.start_date.year,
                                                         self.start_date.month)[1], 0,
                                          0) + relativedelta(months=-12 / self.annual_payments)
                else:
                    dt0 = self.start_date
            else:
                dt0 = max(self.first_payment_date, self.start_date) + relativedelta(
                    months=-12 / self.annual_payments)

            # take care of special payments
            special_payments_schedule_raw = []
            special_payments_schedule = []
            special_payments_dates = []
            if len(self.special_payments_schedule) > 0:
                for i in range(len(self.special_payments_schedule)):
                    for j in range(len(self.special_payments_schedule[i])):
                        special_payments_schedule_raw.append(
                            [self.special_payments_schedule[i][j].date,
                             self.special_payments_schedule[i][j].special_principal_amount])
                        if self.special_payments_schedule[i][j].date not in special_payments_dates:
                            special_payments_dates.append(self.special_payments_schedule[i][j].date)

            for i in range(len(special_payments_dates)):
                amt = self._quantize(str(0))
                for j in range(len(special_payments_schedule_raw)):
                    if special_payments_schedule_raw[j][0] == special_payments_dates[i]:
                        amt += special_payments_schedule_raw[j][1]
                special_payments_schedule.append([special_payments_dates[i], amt])

            # calculate payment schedule
            m = 0
            for i in range(1, self.no_of_payments + 1):

                date = dt0 + relativedelta(months=i * 12 / self.annual_payments)
                if self.payment_end_of_month == True and self.first_payment_date is None:
                    eom_day = cal.monthrange(date.year, date.month)[1]
                    date = date.replace(day=eom_day)  # dt.datetime(date.year,date.month,eom_day)

                special_principal_amount = self._quantize(0)
                bop_date = payment_schedule[(i + m) - 1].date
                compounding_factor = Decimal(
                    str(self._get_day_count(bop_date, date, self.compounding_method,
                                            eom=self.payment_end_of_month)))
                balance_bop = self._quantize(payment_schedule[(i + m) - 1].loan_balance_amount)

                for j in range(len(special_payments_schedule)):
                    if date == special_payments_schedule[j][0]:
                        special_principal_amount = special_payments_schedule[j][1]
                    if (bop_date < special_payments_schedule[j][0] and special_payments_schedule[j][
                        0] < date):
                        # handle special payment inserts
                        compounding_factor = Decimal(
                            str(self._get_day_count(bop_date, special_payments_schedule[j][0],
                                                    self.compounding_method,
                                                    eom=self.payment_end_of_month)))
                        interest_amount = self._quantize(0) if balance_bop == Decimal(
                            str(0)) else self._quantize(
                            balance_bop * self.interest_rate * compounding_factor)
                        principal_amount = self._quantize(0)
                        special_principal_amount = self._quantize(0) if balance_bop == Decimal(
                            str(0)) else min(special_payments_schedule[j][1] - interest_amount,
                                             balance_bop)
                        total_principal_amount = min(principal_amount + special_principal_amount,
                                                     balance_bop)
                        total_payment_amount = total_principal_amount + interest_amount
                        balance_eop = max(balance_bop - total_principal_amount, self._quantize(0))
                        payment = Payment(date=special_payments_schedule[j][0],
                                          payment_amount=total_payment_amount,
                                          interest_amount=interest_amount,
                                          principal_amount=principal_amount,
                                          special_principal_amount=special_principal_amount,
                                          total_principal_amount=special_principal_amount,
                                          loan_balance_amount=balance_eop)
                        payment_schedule.append(payment)
                        m += 1
                        # handle regular payment inserts : update bop_date and bop_date, and special_principal_amount
                        bop_date = special_payments_schedule[j][0]
                        balance_bop = balance_eop
                        special_principal_amount = self._quantize(0)
                        compounding_factor = Decimal(
                            str(self._get_day_count(bop_date, date, self.compounding_method,
                                                    eom=self.payment_end_of_month)))

                interest_amount = self._quantize(0) if balance_bop == Decimal(
                    str(0)) else self._quantize(
                    balance_bop * self.interest_rate * compounding_factor)

                principal_amount = self._quantize(0) if balance_bop == Decimal(
                    str(0)) or interest_only_period >= i else min(
                    self._quantize(regular_principal_payment_amount) - (
                        interest_amount if self.loan_type == 'annuity' else 0), balance_bop)
                special_principal_amount = min(balance_bop - principal_amount,
                                               special_principal_amount) if interest_only_period < i else self._quantize(
                    0)
                total_principal_amount = min(principal_amount + special_principal_amount,
                                             balance_bop)
                total_payment_amount = total_principal_amount + interest_amount
                balance_eop = max(balance_bop - total_principal_amount, self._quantize(0))

                payment = Payment(date=date, payment_amount=total_payment_amount,
                                  interest_amount=interest_amount,
                                  principal_amount=principal_amount,
                                  special_principal_amount=special_principal_amount,
                                  total_principal_amount=total_principal_amount,
                                  loan_balance_amount=balance_eop)
                payment_schedule.append(payment)

            return payment_schedule

    def add_special_payment(self, payment_amount, first_payment_date, special_payment_term,
                            annual_payments):
        special_payment = Special_Payment(payment_amount=payment_amount,
                                          first_payment_date=first_payment_date,
                                          special_payment_term=special_payment_term,
                                          annual_payments=annual_payments)
        self.special_payments.append(special_payment)
        self.special_payments_schedule.append(
            self._get_special_payment_schedule(self, special_payment))

    def get_loan_summary(self):
        payment_schedule = self.get_payment_schedule()
        total_payment_amount = 0
        total_interest_amount = 0
        total_principal_amount = 0
        repayment_to_principal = 0

        for payment in payment_schedule:
            total_payment_amount += payment.payment_amount
            total_interest_amount += payment.interest_amount
            total_principal_amount += payment.total_principal_amount

        repayment_to_principal = self._quantize(total_payment_amount / total_principal_amount)
        loan_summary = Loan_Summary(loan_amount=self._quantize(self.loan_amount),
                                    total_payment_amount=total_payment_amount,
                                    total_principal_amount=total_principal_amount,
                                    total_interest_amount=total_interest_amount,
                                    residual_loan_balance=self._quantize(
                                        self.loan_amount - total_principal_amount),
                                    repayment_to_principal=repayment_to_principal)

        return loan_summary
