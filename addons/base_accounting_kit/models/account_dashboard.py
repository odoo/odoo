# -*- coding: utf-8 -*-

import calendar
import datetime
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, api
from odoo.http import request


class DashBoard(models.Model):
    _inherit = 'account.move'

    # function to getting expenses

    # function to getting income of this year

    @api.model
    def get_income_this_year(self, *post):

        company_id = self.get_current_company_value()

        month_list = []
        for i in range(11, -1, -1):
            l_month = datetime.now() - relativedelta(months=i)
            text = format(l_month, '%B')
            month_list.append(text)

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select sum(debit)-sum(credit) as income ,to_char(account_move_line.date, 'Month')  as month ,
                             internal_group from account_move_line ,account_account where 
                             account_move_line.account_id=account_account.id AND internal_group = 'income' 
                             AND to_char(DATE(NOW()), 'YY') = to_char(account_move_line.date, 'YY')
                             AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                             AND %s 
                             group by internal_group,month                  
                        ''') % (states_arg))
        record = self._cr.dictfetchall()

        self._cr.execute(('''select sum(debit)-sum(credit) as expense ,to_char(account_move_line.date, 'Month')  as month ,
                            internal_group from account_move_line ,account_account where 
                            account_move_line.account_id=account_account.id AND internal_group = 'expense' 
                            AND to_char(DATE(NOW()), 'YY') = to_char(account_move_line.date, 'YY')
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                            AND %s 
                            group by internal_group,month                  
                        ''') % (states_arg))

        result = self._cr.dictfetchall()
        records = []
        for month in month_list:
            last_month_inc = list(filter(lambda m: m['month'].strip() == month, record))
            last_month_exp = list(filter(lambda m: m['month'].strip() == month, result))
            if not last_month_inc and not last_month_exp:
                records.append({
                    'month': month,
                    'income': 0.0,
                    'expense': 0.0,
                    'profit': 0.0,
                })
            elif (not last_month_inc) and last_month_exp:
                last_month_exp[0].update({
                    'income': 0.0,
                    'expense': -1 * last_month_exp[0]['expense'] if last_month_exp[0]['expense'] < 1 else
                    last_month_exp[0]['expense']
                })
                last_month_exp[0].update({
                    'profit': last_month_exp[0]['income'] - last_month_exp[0]['expense']
                })
                records.append(last_month_exp[0])
            elif (not last_month_exp) and last_month_inc:
                last_month_inc[0].update({
                    'expense': 0.0,
                    'income': -1 * last_month_inc[0]['income'] if last_month_inc[0]['income'] < 1 else
                    last_month_inc[0]['income']
                })
                last_month_inc[0].update({
                    'profit': last_month_inc[0]['income'] - last_month_inc[0]['expense']
                })
                records.append(last_month_inc[0])
            else:
                last_month_inc[0].update({
                    'income': -1 * last_month_inc[0]['income'] if last_month_inc[0]['income'] < 1 else
                    last_month_inc[0]['income'],
                    'expense': -1 * last_month_exp[0]['expense'] if last_month_exp[0]['expense'] < 1 else
                    last_month_exp[0]['expense']
                })
                last_month_inc[0].update({
                    'profit': last_month_inc[0]['income'] - last_month_inc[0]['expense']
                })
                records.append(last_month_inc[0])
        income = []
        expense = []
        month = []
        profit = []
        for rec in records:
            income.append(rec['income'])
            expense.append(rec['expense'])
            month.append(rec['month'])
            profit.append(rec['profit'])
        return {
            'income': income,
            'expense': expense,
            'month': month,
            'profit': profit,
        }

    # function to getting income of last year

    @api.model
    def get_income_last_year(self, *post):

        company_id = self.get_current_company_value()

        month_list = []
        for i in range(11, -1, -1):
            l_month = datetime.now() - relativedelta(months=i)
            text = format(l_month, '%B')
            month_list.append(text)

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select sum(debit)-sum(credit) as income ,to_char(account_move_line.date, 'Month')  as month ,
                            internal_group from account_move_line ,account_account
                            where account_move_line.account_id=account_account.id AND internal_group = 'income' 
                            AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW())) -1 
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                            AND %s
                            group by internal_group,month                  
                 ''') % (states_arg))
        record = self._cr.dictfetchall()

        self._cr.execute(('''select sum(debit)-sum(credit) as expense ,to_char(account_move_line.date, 'Month')  as month ,
                            internal_group from account_move_line , account_account where 
                            account_move_line.account_id=account_account.id AND internal_group = 'expense' 
                            AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW())) -1 
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                            AND %s 
                            group by internal_group,month                  
                         ''') % (states_arg))

        result = self._cr.dictfetchall()
        records = []
        for month in month_list:
            last_month_inc = list(filter(lambda m: m['month'].strip() == month, record))
            last_month_exp = list(filter(lambda m: m['month'].strip() == month, result))
            if not last_month_inc and not last_month_exp:
                records.append({
                    'month': month,
                    'income': 0.0,
                    'expense': 0.0,
                    'profit': 0.0,
                })
            elif (not last_month_inc) and last_month_exp:
                last_month_exp[0].update({
                    'income': 0.0,
                    'expense': -1 * last_month_exp[0]['expense'] if last_month_exp[0]['expense'] < 1 else
                    last_month_exp[0]['expense']
                })
                last_month_exp[0].update({
                    'profit': last_month_exp[0]['income'] - last_month_exp[0]['expense']
                })
                records.append(last_month_exp[0])
            elif (not last_month_exp) and last_month_inc:
                last_month_inc[0].update({
                    'expense': 0.0,
                    'income': -1 * last_month_inc[0]['income'] if last_month_inc[0]['income'] < 1 else
                    last_month_inc[0]['income']
                })
                last_month_inc[0].update({
                    'profit': last_month_inc[0]['income'] - last_month_inc[0]['expense']
                })
                records.append(last_month_inc[0])
            else:
                last_month_inc[0].update({
                    'income': -1 * last_month_inc[0]['income'] if last_month_inc[0]['income'] < 1 else
                    last_month_inc[0]['income'],
                    'expense': -1 * last_month_exp[0]['expense'] if last_month_exp[0]['expense'] < 1 else
                    last_month_exp[0]['expense']
                })
                last_month_inc[0].update({
                    'profit': last_month_inc[0]['income'] - last_month_inc[0]['expense']
                })
                records.append(last_month_inc[0])
        income = []
        expense = []
        month = []
        profit = []
        for rec in records:
            income.append(rec['income'])
            expense.append(rec['expense'])
            month.append(rec['month'])
            profit.append(rec['profit'])
        return {
            'income': income,
            'expense': expense,
            'month': month,
            'profit': profit,
        }

    # function to getting income of last month

    @api.model
    def get_income_last_month(self, *post):

        company_id = self.get_current_company_value()
        day_list = []
        now = datetime.now()
        day = \
            calendar.monthrange(now.year - 1 if now.month == 1 else now.year,
                                now.month - 1 if not now.month == 1 else 12)[
                1]

        for x in range(1, day + 1):
            day_list.append(x)

        one_month_ago = (datetime.now() - relativedelta(months=1)).month

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select sum(debit)-sum(credit) as income ,cast(to_char(account_move_line.date, 'DD')as int)
                            as date , internal_group from account_move_line , account_account where   
                            Extract(month FROM account_move_line.date) in ''' + str(tuple(company_id)) + ''' 
                            AND %s
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + ''' 
                            AND account_move_line.account_id=account_account.id AND internal_group='income'   
                            group by internal_group,date                 
                             ''') % (states_arg))

        record = self._cr.dictfetchall()

        self._cr.execute(('''select sum(debit)-sum(credit) as expense ,cast(to_char(account_move_line.date, 'DD')as int)
                            as date ,internal_group from account_move_line ,account_account where  
                            Extract(month FROM account_move_line.date) in ''' + str(tuple(company_id)) + ''' 
                            AND %s
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + ''' 
                            AND account_move_line.account_id=account_account.id AND internal_group='expense'
                            group by internal_group,date                 
                                 ''') % (states_arg))
        result = self._cr.dictfetchall()
        records = []
        for date in day_list:
            last_month_inc = list(filter(lambda m: m['date'] == date, record))
            last_month_exp = list(filter(lambda m: m['date'] == date, result))
            if not last_month_inc and not last_month_exp:
                records.append({
                    'date': date,
                    'income': 0.0,
                    'expense': 0.0,
                    'profit': 0.0
                })
            elif (not last_month_inc) and last_month_exp:
                last_month_exp[0].update({
                    'income': 0.0,
                    'expense': -1 * last_month_exp[0]['expense'] if last_month_exp[0]['expense'] < 1 else
                    last_month_exp[0]['expense']
                })
                last_month_exp[0].update({
                    'profit': last_month_exp[0]['income'] - last_month_exp[0]['expense']
                })
                records.append(last_month_exp[0])
            elif (not last_month_exp) and last_month_inc:
                last_month_inc[0].update({
                    'expense': 0.0,
                    'income': -1 * last_month_inc[0]['income'] if last_month_inc[0]['income'] < 1 else
                    last_month_inc[0]['income']
                })
                last_month_inc[0].update({
                    'profit': last_month_inc[0]['income'] - last_month_inc[0]['expense']
                })
                records.append(last_month_inc[0])
            else:
                last_month_inc[0].update({
                    'income': -1 * last_month_inc[0]['income'] if last_month_inc[0]['income'] < 1 else
                    last_month_inc[0]['income'],
                    'expense': -1 * last_month_exp[0]['expense'] if last_month_exp[0]['expense'] < 1 else
                    last_month_exp[0]['expense']
                })
                last_month_inc[0].update({
                    'profit': last_month_inc[0]['income'] - last_month_inc[0]['expense']
                })
                records.append(last_month_inc[0])
        income = []
        expense = []
        date = []
        profit = []
        for rec in records:
            income.append(rec['income'])
            expense.append(rec['expense'])
            date.append(rec['date'])
            profit.append(rec['profit'])
        return {
            'income': income,
            'expense': expense,
            'date': date,
            'profit': profit

        }

    # function to getting income of this month

    @api.model
    def get_income_this_month(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        day_list = []
        now = datetime.now()
        day = calendar.monthrange(now.year, now.month)[1]
        for x in range(1, day + 1):
            day_list.append(x)

        self._cr.execute(('''select sum(debit)-sum(credit) as income ,cast(to_char(account_move_line.date, 'DD')as int)
                            as date , internal_group from account_move_line , account_account
                            where   Extract(month FROM account_move_line.date) = Extract(month FROM DATE(NOW()))  
                            AND Extract(YEAR FROM account_move_line.date) = Extract(YEAR FROM DATE(NOW()))  
                            AND %s
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + ''' 
                            AND account_move_line.account_id=account_account.id AND internal_group='income'
                            group by internal_group,date                 
                        ''') % (states_arg))

        record = self._cr.dictfetchall()

        self._cr.execute(('''select sum(debit)-sum(credit) as expense ,cast(to_char(account_move_line.date, 'DD')as int)
                            as date , internal_group from account_move_line , account_account where  
                            Extract(month FROM account_move_line.date) = Extract(month FROM DATE(NOW()))  
                            AND Extract(YEAR FROM account_move_line.date) = Extract(YEAR FROM DATE(NOW()))  
                            AND %s
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + ''' 
                            AND account_move_line.account_id=account_account.id AND internal_group='expense'
                            group by internal_group,date                 
                         ''') % (states_arg))
        result = self._cr.dictfetchall()
        records = []
        for date in day_list:
            last_month_inc = list(filter(lambda m: m['date'] == date, record))
            last_month_exp = list(filter(lambda m: m['date'] == date, result))
            if not last_month_inc and not last_month_exp:
                records.append({
                    'date': date,
                    'income': 0.0,
                    'expense': 0.0,
                    'profit': 0.0
                })
            elif (not last_month_inc) and last_month_exp:
                last_month_exp[0].update({
                    'income': 0.0,
                    'expense': -1 * last_month_exp[0]['expense'] if last_month_exp[0]['expense'] < 1 else
                    last_month_exp[0]['expense']
                })
                last_month_exp[0].update({
                    'profit': last_month_exp[0]['income'] - last_month_exp[0]['expense']
                })
                records.append(last_month_exp[0])
            elif (not last_month_exp) and last_month_inc:
                last_month_inc[0].update({
                    'expense': 0.0,
                    'income': -1 * last_month_inc[0]['income'] if last_month_inc[0]['income'] < 1 else
                    last_month_inc[0]['income']
                })
                last_month_inc[0].update({
                    'profit': last_month_inc[0]['income'] - last_month_inc[0]['expense']
                })
                records.append(last_month_inc[0])
            else:
                last_month_inc[0].update({
                    'income': -1 * last_month_inc[0]['income'] if last_month_inc[0]['income'] < 1 else
                    last_month_inc[0]['income'],
                    'expense': -1 * last_month_exp[0]['expense'] if last_month_exp[0]['expense'] < 1 else
                    last_month_exp[0]['expense']
                })
                last_month_inc[0].update({
                    'profit': last_month_inc[0]['income'] - last_month_inc[0]['expense']
                })
                records.append(last_month_inc[0])
        income = []
        expense = []
        date = []
        profit = []
        for rec in records:
            income.append(rec['income'])
            expense.append(rec['expense'])
            date.append(rec['date'])
            profit.append(rec['profit'])
        return {
            'income': income,
            'expense': expense,
            'date': date,
            'profit': profit

        }

    # function to getting late bills

    @api.model
    def get_latebills(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        self._cr.execute(('''  select res_partner.name as partner, res_partner.commercial_partner_id as res  ,
                            account_move.commercial_partner_id as parent, sum(account_move.amount_total) as amount
                            from account_move,res_partner where 
                            account_move.partner_id=res_partner.id AND account_move.move_type = 'in_invoice' AND
                            payment_state = 'not_paid' AND 
                              account_move.company_id in ''' + str(tuple(company_id)) + ''' AND
                            %s 
                            AND  account_move.commercial_partner_id=res_partner.commercial_partner_id 
                            group by parent,partner,res
                            order by amount desc ''') % (states_arg))

        record = self._cr.dictfetchall()

        bill_partner = [item['partner'] for item in record]

        bill_amount = [item['amount'] for item in record]

        amounts = sum(bill_amount[9:])
        name = bill_partner[9:]
        results = []
        pre_partner = []

        bill_amount = bill_amount[:9]
        bill_amount.append(amounts)
        bill_partner = bill_partner[:9]
        bill_partner.append("Others")
        records = {
            'bill_partner': bill_partner,
            'bill_amount': bill_amount,
            'result': results,

        }
        return records

        # return record

    # function to getting over dues

    @api.model
    def get_overdues(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        self._cr.execute((''' select res_partner.name as partner, res_partner.commercial_partner_id as res,
                             account_move.commercial_partner_id as parent, sum(account_move.amount_total) as amount
                            from account_move, account_move_line, res_partner, account_account where 
                            account_move.partner_id=res_partner.id AND account_move.move_type = 'out_invoice' 
                            AND payment_state = 'not_paid' 
                            AND %s
                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                            AND account_account.internal_type = 'payable'
                            AND account_move.commercial_partner_id=res_partner.commercial_partner_id 
                            group by parent,partner,res
                            order by amount desc
                            ''') % (states_arg))
        record = self._cr.dictfetchall()
        due_partner = [item['partner'] for item in record]
        due_amount = [item['amount'] for item in record]

        amounts = sum(due_amount[9:])
        name = due_partner[9:]
        result = []
        pre_partner = []

        due_amount = due_amount[:9]
        due_amount.append(amounts)
        due_partner = due_partner[:9]
        due_partner.append("Others")
        records = {
            'due_partner': due_partner,
            'due_amount': due_amount,
            'result': result,

        }
        return records

    @api.model
    def get_overdues_this_month_and_year(self, *post):

        states_arg = ""
        if post[0] != 'posted':
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        company_id = self.get_current_company_value()
        if post[1] == 'this_month':
            self._cr.execute((''' 
                               select to_char(account_move.date, 'Month') as month, res_partner.name as due_partner, account_move.partner_id as parent,
                               sum(account_move.amount_total) as amount from account_move, res_partner where account_move.partner_id = res_partner.id
                               AND account_move.move_type = 'out_invoice'
                               AND payment_state = 'not_paid'
                               AND %s 
                               AND Extract(month FROM account_move.invoice_date_due) = Extract(month FROM DATE(NOW()))
                               AND Extract(YEAR FROM account_move.invoice_date_due) = Extract(YEAR FROM DATE(NOW()))
                               AND account_move.partner_id = res_partner.commercial_partner_id
                               AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                               group by parent, due_partner, month
                               order by amount desc ''') % (states_arg))
        else:
            self._cr.execute((''' select  res_partner.name as due_partner, account_move.partner_id as parent,
                                            sum(account_move.amount_total) as amount from account_move, res_partner where account_move.partner_id = res_partner.id
                                            AND account_move.move_type = 'out_invoice'
                                            AND payment_state = 'not_paid'
                                            AND %s
                                            AND Extract(YEAR FROM account_move.invoice_date_due) = Extract(YEAR FROM DATE(NOW()))
                                            AND account_move.partner_id = res_partner.commercial_partner_id
                                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
    
                                            group by parent, due_partner
                                            order by amount desc ''') % (states_arg))

        record = self._cr.dictfetchall()
        due_partner = [item['due_partner'] for item in record]
        due_amount = [item['amount'] for item in record]

        amounts = sum(due_amount[9:])
        name = due_partner[9:]
        result = []
        pre_partner = []

        due_amount = due_amount[:9]
        due_amount.append(amounts)
        due_partner = due_partner[:9]
        due_partner.append("Others")
        records = {
            'due_partner': due_partner,
            'due_amount': due_amount,
            'result': result,

        }
        return records

    @api.model
    def get_latebillss(self, *post):
        company_id = self.get_current_company_value()

        partners = self.env['res.partner'].search([('active', '=', True)])

        states_arg = ""
        if post[0] != 'posted':
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        if post[1] == 'this_month':
            self._cr.execute((''' 
                                select to_char(account_move.date, 'Month') as month, res_partner.name as bill_partner, account_move.partner_id as parent,
                                sum(account_move.amount_total) as amount from account_move, res_partner where account_move.partner_id = res_partner.id
                                AND account_move.move_type = 'in_invoice'
                                AND payment_state = 'not_paid'
                                AND %s 
                                AND Extract(month FROM account_move.invoice_date_due) = Extract(month FROM DATE(NOW()))
                                AND Extract(YEAR FROM account_move.invoice_date_due) = Extract(YEAR FROM DATE(NOW()))
                                AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                AND account_move.partner_id = res_partner.commercial_partner_id
                                group by parent, bill_partner, month
                                order by amount desc ''') % (states_arg))
        else:
            self._cr.execute((''' select res_partner.name as bill_partner, account_move.partner_id as parent,
                                            sum(account_move.amount_total) as amount from account_move, res_partner where account_move.partner_id = res_partner.id
                                            AND account_move.move_type = 'in_invoice'
                                            AND payment_state = 'not_paid'
                                            AND %s
                                            AND Extract(YEAR FROM account_move.invoice_date_due) = Extract(YEAR FROM DATE(NOW()))
                                            AND account_move.partner_id = res_partner.commercial_partner_id
                                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                            group by parent, bill_partner
                                            order by amount desc ''') % (states_arg))

        result = self._cr.dictfetchall()
        bill_partner = [item['bill_partner'] for item in result]

        bill_amount = [item['amount'] for item in result]

        amounts = sum(bill_amount[9:])
        name = bill_partner[9:]
        results = []
        pre_partner = []

        bill_amount = bill_amount[:9]
        bill_amount.append(amounts)
        bill_partner = bill_partner[:9]
        bill_partner.append("Others")
        records = {
            'bill_partner': bill_partner,
            'bill_amount': bill_amount,
            'result': results,

        }
        return records

    @api.model
    def get_top_10_customers_month(self, *post):
        record_invoice = {}
        record_refund = {}
        company_id = self.get_current_company_value()
        states_arg = ""
        if post[0] != 'posted':
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""
        if post[1] == 'this_month':
            self._cr.execute((''' select res_partner.name as customers, account_move.commercial_partner_id as parent, 
                                    sum(account_move.amount_total) as amount from account_move, res_partner
                                    where account_move.commercial_partner_id = res_partner.id
                                    AND account_move.company_id in %s 
                                    AND account_move.move_type = 'out_invoice' 
                                    AND %s   
                                    AND Extract(month FROM account_move.invoice_date) = Extract(month FROM DATE(NOW()))
                                    AND Extract(YEAR FROM account_move.invoice_date) = Extract(YEAR FROM DATE(NOW()))                      
                                    group by parent, customers
                                    order by amount desc 
                                    limit 10
                                    ''') % (tuple(company_id), states_arg))
            record_invoice = self._cr.dictfetchall()
            self._cr.execute((''' select res_partner.name as customers, account_move.commercial_partner_id as parent, 
                                    sum(account_move.amount_total) as amount from account_move, res_partner
                                    where account_move.commercial_partner_id = res_partner.id
                                    AND account_move.company_id in %s
                                    AND account_move.move_type = 'out_refund' 
                                    AND %s      
                                    AND Extract(month FROM account_move.invoice_date) = Extract(month FROM DATE(NOW()))
                                    AND Extract(YEAR FROM account_move.invoice_date) = Extract(YEAR FROM DATE(NOW()))                   
                                    group by parent, customers
                                    order by amount desc 
                                    limit 10
                                    ''') % (tuple(company_id), states_arg))
            record_refund = self._cr.dictfetchall()
        else:
            one_month_ago = (datetime.now() - relativedelta(months=1)).month
            self._cr.execute((''' select res_partner.name as customers, account_move.commercial_partner_id as parent, 
                                            sum(account_move.amount_total) as amount from account_move, res_partner
                                            where account_move.commercial_partner_id = res_partner.id
                                            AND account_move.company_id in %s
                                            AND account_move.move_type = 'out_invoice' 
                                            AND %s            
                                            AND Extract(month FROM account_move.invoice_date) = ''' + str(
                one_month_ago) + '''
                                            group by parent, customers
                                            order by amount desc 
                                            limit 10
                                            ''') % (tuple(company_id), states_arg))
            record_invoice = self._cr.dictfetchall()
            self._cr.execute((''' select res_partner.name as customers, account_move.commercial_partner_id as parent, 
                                            sum(account_move.amount_total) as amount from account_move, res_partner
                                            where account_move.commercial_partner_id = res_partner.id
                                            AND account_move.company_id in %s 
                                            AND account_move.move_type = 'out_refund' 
                                            AND %s       
                                            AND Extract(month FROM account_move.invoice_date) = ''' + str(
                one_month_ago) + '''                  
                                            group by parent, customers
                                            order by amount desc 
                                            limit 10
                                            ''') % (tuple(company_id), states_arg))
            record_refund = self._cr.dictfetchall()
        summed = []
        for out_sum in record_invoice:
            parent = out_sum['parent']
            su = out_sum['amount'] - \
                 (list(filter(lambda refund: refund['parent'] == out_sum['parent'], record_refund))[0][
                      'amount'] if len(
                     list(filter(lambda refund: refund['parent'] == out_sum['parent'], record_refund))) > 0 else 0.0)
            summed.append({
                'customers': out_sum['customers'],
                'amount': su,
                'parent': parent
            })
        return summed

    # function to get total invoice

    @api.model
    def get_total_invoice(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        self._cr.execute(('''select sum(amount_total) as customer_invoice from account_move where move_type ='out_invoice'
                            AND  %s  AND account_move.company_id in ''' + str(tuple(company_id)) + '''           
                        ''') % (states_arg))
        record_customer = self._cr.dictfetchall()

        self._cr.execute(('''select sum(amount_total) as supplier_invoice from account_move where move_type ='in_invoice' 
                          AND  %s  AND account_move.company_id in ''' + str(tuple(company_id)) + '''      
                        ''') % (states_arg))
        record_supplier = self._cr.dictfetchall()

        self._cr.execute(('''select sum(amount_total) as credit_note from account_move where move_type ='out_refund'
                          AND  %s  AND account_move.company_id in ''' + str(tuple(company_id)) + '''      
                        ''') % (states_arg))
        result_credit_note = self._cr.dictfetchall()

        self._cr.execute(('''select sum(amount_total) as refund from account_move where move_type ='in_refund'
                          AND  %s  AND account_move.company_id in ''' + str(tuple(company_id)) + '''   
                        ''') % (states_arg))
        result_refund = self._cr.dictfetchall()

        customer_invoice = [item['customer_invoice'] for item in record_customer]
        supplier_invoice = [item['supplier_invoice'] for item in record_supplier]
        credit_note = [item['credit_note'] for item in result_credit_note]
        refund = [item['refund'] for item in result_refund]

        return customer_invoice, credit_note, supplier_invoice, refund

    @api.model
    def get_total_invoice_current_year(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        self._cr.execute(('''select sum(amount_total_signed) as customer_invoice from account_move where move_type ='out_invoice'
                            AND   %s                               
                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))     
                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''           
                        ''') % (states_arg))
        record_customer_current_year = self._cr.dictfetchall()

        self._cr.execute(('''select sum(-(amount_total_signed)) as supplier_invoice from account_move where move_type ='in_invoice'
                            AND  %s                              
                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))     
                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''      
                        ''') % (states_arg))
        record_supplier_current_year = self._cr.dictfetchall()
        result_credit_note_current_year = [{'credit_note': 0.0}]
        result_refund_current_year = [{'refund': 0.0}]
        self._cr.execute(('''select sum(amount_total_signed) - sum(amount_residual_signed)  as customer_invoice_paid from account_move where move_type ='out_invoice'
                                    AND   %s
                                    AND payment_state = 'paid'
                                    AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                    AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                ''') % (states_arg))
        record_paid_customer_invoice_current_year = self._cr.dictfetchall()

        self._cr.execute(('''select sum(-(amount_total_signed)) - sum(-(amount_residual_signed))  as supplier_invoice_paid from account_move where move_type ='in_invoice'
                                    AND   %s
                                    AND  payment_state = 'paid'
                                    AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                    AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                ''') % (states_arg))
        result_paid_supplier_invoice_current_year = self._cr.dictfetchall()
        record_paid_customer_credit_current_year = [{'customer_credit_paid': 0.0}]
        result_paid_supplier_refund_current_year = [{'supplier_refund_paid': 0.0}]
        customer_invoice_current_year = [item['customer_invoice'] for item in record_customer_current_year]
        supplier_invoice_current_year = [item['supplier_invoice'] for item in record_supplier_current_year]

        credit_note_current_year = [item['credit_note'] for item in result_credit_note_current_year]
        refund_current_year = [item['refund'] for item in result_refund_current_year]

        paid_customer_invoice_current_year = [item['customer_invoice_paid'] for item in
                                              record_paid_customer_invoice_current_year]
        paid_supplier_invoice_current_year = [item['supplier_invoice_paid'] for item in
                                              result_paid_supplier_invoice_current_year]

        paid_customer_credit_current_year = [item['customer_credit_paid'] for item in
                                             record_paid_customer_credit_current_year]
        paid_supplier_refund_current_year = [item['supplier_refund_paid'] for item in
                                             result_paid_supplier_refund_current_year]

        return customer_invoice_current_year, credit_note_current_year, supplier_invoice_current_year, refund_current_year, paid_customer_invoice_current_year, paid_supplier_invoice_current_year, paid_customer_credit_current_year, paid_supplier_refund_current_year

    @api.model
    def get_total_invoice_current_month(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        self._cr.execute(('''select sum(amount_total_signed) as customer_invoice from account_move where move_type ='out_invoice'
                                    AND   %s                               
                                    AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))
                                    AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))     
                                    AND account_move.company_id in ''' + str(tuple(company_id)) + '''           
                                ''') % (states_arg))
        record_customer_current_month = self._cr.dictfetchall()

        self._cr.execute(('''select sum(-(amount_total_signed)) as supplier_invoice from account_move where move_type ='in_invoice'
                                    AND  %s                              
                                    AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))
                                    AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))     
                                    AND account_move.company_id in ''' + str(tuple(company_id)) + '''      
                                ''') % (states_arg))
        record_supplier_current_month = self._cr.dictfetchall()
        result_credit_note_current_month = [{'credit_note': 0.0}]
        result_refund_current_month = [{'refund': 0.0}]
        self._cr.execute(('''select sum(amount_total_signed) - sum(amount_residual_signed)  as customer_invoice_paid from account_move where move_type ='out_invoice'
                                            AND   %s
                                            AND payment_state = 'paid'
                                            AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))
                                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                        ''') % (states_arg))
        record_paid_customer_invoice_current_month = self._cr.dictfetchall()

        self._cr.execute(('''select sum(-(amount_total_signed)) - sum(-(amount_residual_signed))  as supplier_invoice_paid from account_move where move_type ='in_invoice'
                                            AND   %s
                                            AND payment_state = 'paid'
                                            AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))
                                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                        ''') % (states_arg))
        result_paid_supplier_invoice_current_month = self._cr.dictfetchall()
        record_paid_customer_credit_current_month = [{'customer_credit_paid': 0.0}]
        result_paid_supplier_refund_current_month = [{'supplier_refund_paid': 0.0}]

        customer_invoice_current_month = [item['customer_invoice'] for item in record_customer_current_month]
        supplier_invoice_current_month = [item['supplier_invoice'] for item in record_supplier_current_month]
        credit_note_current_month = [item['credit_note'] for item in result_credit_note_current_month]
        refund_current_month = [item['refund'] for item in result_refund_current_month]
        paid_customer_invoice_current_month = [item['customer_invoice_paid'] for item in
                                               record_paid_customer_invoice_current_month]
        paid_supplier_invoice_current_month = [item['supplier_invoice_paid'] for item in
                                               result_paid_supplier_invoice_current_month]

        paid_customer_credit_current_month = [item['customer_credit_paid'] for item in
                                              record_paid_customer_credit_current_month]
        paid_supplier_refund_current_month = [item['supplier_refund_paid'] for item in
                                              result_paid_supplier_refund_current_month]

        currency = self.get_currency()
        return customer_invoice_current_month, credit_note_current_month, supplier_invoice_current_month, refund_current_month, paid_customer_invoice_current_month, paid_supplier_invoice_current_month, paid_customer_credit_current_month, paid_supplier_refund_current_month, currency

    @api.model
    def get_total_invoice_this_month(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        self._cr.execute(('''select sum(amount_total) from account_move where move_type = 'out_invoice' 
                            AND %s
                            AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))      
                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))   
                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                            ''') % (states_arg))
        record = self._cr.dictfetchall()
        return record

    # function to get total invoice last month

    @api.model
    def get_total_invoice_last_month(self):

        one_month_ago = (datetime.now() - relativedelta(months=1)).month

        self._cr.execute('''select sum(amount_total) from account_move where move_type = 'out_invoice' AND
                               account_move.state = 'posted'
                            AND Extract(month FROM account_move.date) = ''' + str(one_month_ago) + ''' 
                            ''')
        record = self._cr.dictfetchall()
        return record

    # function to get total invoice last year

    @api.model
    def get_total_invoice_last_year(self):

        self._cr.execute(''' select sum(amount_total) from account_move where move_type = 'out_invoice' 
                            AND account_move.state = 'posted'
                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW())) - 1    
                                ''')
        record = self._cr.dictfetchall()
        return record

    # function to get total invoice this year

    @api.model
    def get_total_invoice_this_year(self):

        company_id = self.get_current_company_value()

        self._cr.execute(''' select sum(amount_total) from account_move where move_type = 'out_invoice'
                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW())) AND
                               account_move.state = 'posted'   AND
                                account_move.company_id in ''' + str(tuple(company_id)) + '''
                                    ''')
        record = self._cr.dictfetchall()
        return record

    # function to get unreconcile items

    @api.model
    def unreconcile_items(self):
        self._cr.execute('''
                            select count(*) FROM account_move_line l,account_account a
                            where L.account_id=a.id AND l.full_reconcile_id IS NULL AND 
                            l.balance != 0 AND a.reconcile IS TRUE ''')
        record = self._cr.dictfetchall()
        return record

    # function to get unreconcile items this month

    @api.model
    def unreconcile_items_this_month(self, *post):
        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        qry = ''' select count(*) FROM account_move_line l,account_account a
                              where Extract(month FROM l.date) = Extract(month FROM DATE(NOW())) AND
                              Extract(YEAR FROM l.date) = Extract(YEAR FROM DATE(NOW())) AND
                              L.account_id=a.id AND l.full_reconcile_id IS NULL AND 
                              l.balance != 0 AND a.reconcile IS F 
                              AND l.''' + states_arg + '''
                              AND  l.company_id in ''' + str(tuple(company_id)) + '''                              
                               '''

        self._cr.execute((''' select count(*) FROM account_move_line l,account_account a
                              where Extract(month FROM l.date) = Extract(month FROM DATE(NOW())) AND
                              Extract(YEAR FROM l.date) = Extract(YEAR FROM DATE(NOW())) AND
                              L.account_id=a.id AND l.full_reconcile_id IS NULL AND 
                              l.balance != 0 AND a.reconcile IS TRUE 
                              AND l.%s
                              AND  l.company_id in ''' + str(tuple(company_id)) + '''                              
                               ''') % (states_arg))
        record = self._cr.dictfetchall()
        return record

    # function to get unreconcile items last month

    @api.model
    def unreconcile_items_last_month(self):

        one_month_ago = (datetime.now() - relativedelta(months=1)).month

        self._cr.execute('''  select count(*) FROM account_move_line l,account_account a 
                              where Extract(month FROM l.date) = ''' + str(one_month_ago) + ''' AND
                              L.account_id=a.id AND l.full_reconcile_id IS NULL AND l.balance != 0 AND a.reconcile IS TRUE 
                         ''')
        record = self._cr.dictfetchall()
        return record

    # function to get unreconcile items this year

    @api.model
    def unreconcile_items_this_year(self, *post):
        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''  select count(*) FROM account_move_line l,account_account a
                                  where Extract(year FROM l.date) = Extract(year FROM DATE(NOW())) AND
                                  l.account_id=a.id AND l.full_reconcile_id IS NULL AND 
                                  l.balance != 0 AND a.reconcile IS TRUE  
                                  AND l.%s
                                  AND  l.company_id in ''' + str(tuple(company_id)) + '''       
                                  ''') % (states_arg))
        record = self._cr.dictfetchall()
        return record

    @api.model
    def click_expense_month(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""
        self._cr.execute((''' select account_move_line.id from  account_account, account_move_line where 
                            account_move_line.account_id = account_account.id AND account_account.internal_group = 'expense' AND  
                            %s                
                            AND Extract(month FROM account_move_line.date) = Extract(month FROM DATE(NOW()))
                            AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW())) 
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                                 ''') % (states_arg))
        record = [row[0] for row in self._cr.fetchall()]
        return record

    @api.model
    def click_expense_year(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""
        self._cr.execute((''' select account_move_line.id from  account_account, account_move_line where
                                account_move_line.account_id = account_account.id AND account_account.internal_group = 'expense' AND  
                                %s                         
                                AND Extract(YEAR FROM account_move_line.date) = Extract(YEAR FROM DATE(NOW())) 
                                AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                                ''') % (states_arg))
        record = [row[0] for row in self._cr.fetchall()]
        return record

    @api.model
    def click_total_income_month(self, *post):
        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select account_move_line.id from account_account, account_move_line where
                                account_move_line.account_id = account_account.id AND account_account.internal_group = 'income'
                               AND %s
                               AND Extract(month FROM account_move_line.date) = Extract(month FROM DATE(NOW())) 
                               AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW())) 
                               AND account_move_line.company_id in ''' + str(tuple(company_id)) + ''' 

                                     ''') % (states_arg))
        record = [row[0] for row in self._cr.fetchall()]
        return record

    @api.model
    def click_total_income_year(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute((''' select account_move_line.id from account_account, account_move_line where                           
                             account_move_line.account_id = account_account.id AND account_account.internal_group = 'income'
                             AND %s
                          AND Extract(YEAR FROM account_move_line.date) = Extract(YEAR FROM DATE(NOW())) 
                          AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                        ''') % (states_arg))
        record = [row[0] for row in self._cr.fetchall()]
        return record

    @api.model
    def click_profit_income_month(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select account_move_line.id from  account_account, account_move_line where 
                                       account_move_line.account_id = account_account.id AND
                                       %s AND
                                       (account_account.internal_group = 'income' or    
                                       account_account.internal_group = 'expense' ) 
                                       AND Extract(month FROM account_move_line.date) = Extract(month FROM DATE(NOW())) 
                                       AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW()))   
                                       AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''        
                                        ''') % (states_arg))
        profit = [row[0] for row in self._cr.fetchall()]
        return profit

    @api.model
    def click_profit_income_year(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select account_move_line.id from  account_account, account_move_line where 
                                            account_move_line.account_id = account_account.id AND
                                            %s AND
                                           (account_account.internal_group = 'income' or    
                                           account_account.internal_group = 'expense' )                                       
                                           AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW()))  
                                           AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''           
                                            ''') % (states_arg))
        profit = [row[0] for row in self._cr.fetchall()]
        return profit

    @api.model
    def click_bill_year(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""
        self._cr.execute(('''select account_move.id from account_move where move_type ='in_invoice'
                               AND  %s                              
                               AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))     
                               AND account_move.company_id in ''' + str(tuple(company_id)) + '''      
                           ''') % (states_arg))
        record_supplier_current_year = [row[0] for row in self._cr.fetchall()]
        return record_supplier_current_year

    @api.model
    def click_bill_year_paid(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        self._cr.execute(('''select account_move.id from account_move where move_type ='in_invoice'
                                       AND   %s
                                       AND  payment_state = 'paid'
                                       AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                       AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                   ''') % (states_arg))
        result_paid_supplier_invoice_current_year = [row[0] for row in self._cr.fetchall()]
        return result_paid_supplier_invoice_current_year

    @api.model
    def click_invoice_year_paid(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""
        self._cr.execute(('''select account_move.id from account_move where move_type ='out_invoice'
                                       AND   %s
                                       AND payment_state = 'paid'
                                       AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                       AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                   ''') % (states_arg))
        record_paid_customer_invoice_current_year = [row[0] for row in self._cr.fetchall()]
        return record_paid_customer_invoice_current_year

    @api.model
    def click_invoice_year(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""
        self._cr.execute(('''select account_move.id  from account_move where move_type ='out_invoice'
                               AND   %s                               
                               AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))     
                               AND account_move.company_id in ''' + str(tuple(company_id)) + '''           
                           ''') % (states_arg))
        record_customer_current_year = [row[0] for row in self._cr.fetchall()]
        return record_customer_current_year

    @api.model
    def click_bill_month(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""
        self._cr.execute(('''select account_move.id from account_move where move_type ='in_invoice'
                                            AND   %s
                                            AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))
                                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                        ''') % (states_arg))
        bill_month = [row[0] for row in self._cr.fetchall()]
        return bill_month

    @api.model
    def click_bill_month_paid(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""
        self._cr.execute(('''select account_move.id from account_move where move_type ='in_invoice'
                                            AND   %s
                                            AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))
                                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                            AND payment_state = 'paid'
                                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                        ''') % (states_arg))
        result_paid_supplier_invoice_current_month = [row[0] for row in self._cr.fetchall()]
        return result_paid_supplier_invoice_current_month

    @api.model
    def click_invoice_month_paid(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""
        self._cr.execute(('''select account_move.id from account_move where move_type ='out_invoice'
                                            AND   %s
                                            AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))
                                            AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))
                                            AND payment_state = 'paid'
                                            AND account_move.company_id in ''' + str(tuple(company_id)) + '''
                                        ''') % (states_arg))
        record_paid_customer_invoice_current_month = [row[0] for row in self._cr.fetchall()]
        return record_paid_customer_invoice_current_month

    @api.model
    def click_invoice_month(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""
        self._cr.execute(('''select account_move.id from account_move where move_type ='out_invoice'
                                    AND   %s                               
                                    AND Extract(month FROM account_move.date) = Extract(month FROM DATE(NOW()))
                                    AND Extract(YEAR FROM account_move.date) = Extract(YEAR FROM DATE(NOW()))     
                                    AND account_move.company_id in ''' + str(tuple(company_id)) + '''           
                                ''') % (states_arg))
        record_customer_current_month = [row[0] for row in self._cr.fetchall()]
        return record_customer_current_month

    @api.model
    def click_unreconcile_month(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""
        qry = ''' select count(*) FROM account_move_line l,account_account a
                              where Extract(month FROM l.date) = Extract(month FROM DATE(NOW())) AND
                              Extract(YEAR FROM l.date) = Extract(YEAR FROM DATE(NOW())) AND
                              L.account_id=a.id AND l.full_reconcile_id IS NULL AND 
                              l.balance != 0 AND a.reconcile IS F 
                              AND l.''' + states_arg + '''
                              AND  l.company_id in ''' + str(tuple(company_id)) + '''                              
                               '''

        self._cr.execute((''' select l.id FROM account_move_line l,account_account a
                              where Extract(month FROM l.date) = Extract(month FROM DATE(NOW())) AND
                              Extract(YEAR FROM l.date) = Extract(YEAR FROM DATE(NOW())) AND
                              L.account_id=a.id AND l.full_reconcile_id IS NULL AND 
                              l.balance != 0 AND a.reconcile IS TRUE 
                              AND l.%s
                              AND  l.company_id in ''' + str(tuple(company_id)) + '''                              
                               ''') % (states_arg))
        record = [row[0] for row in self._cr.fetchall()]
        return record

    @api.model
    def click_unreconcile_year(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""
        self._cr.execute(('''  select l.id FROM account_move_line l,account_account a
                                  where Extract(year FROM l.date) = Extract(year FROM DATE(NOW())) AND
                                  L.account_id=a.id AND l.full_reconcile_id IS NULL AND 
                                  l.balance != 0 AND a.reconcile IS TRUE  
                                  AND l.%s
                                  AND  l.company_id in ''' + str(tuple(company_id)) + '''       
                                  ''') % (states_arg))
        record = [row[0] for row in self._cr.fetchall()]
        return record

    # function to get unreconcile items last year

    @api.model
    def unreconcile_items_last_year(self):

        self._cr.execute('''  select count(*) FROM account_move_line l,account_account a
                                      where Extract(year FROM l.date) = Extract(year FROM DATE(NOW())) - 1 AND
                                      L.account_id=a.id AND l.full_reconcile_id IS NULL AND 
                                      l.balance != 0 AND a.reconcile IS TRUE
                                      ''')
        record = self._cr.dictfetchall()
        return record

    # function to get total income

    @api.model
    def month_income(self):

        self._cr.execute(''' select sum(debit) as debit , sum(credit) as credit  from account_move, account_account,account_move_line
                            where  account_move.move_type = 'entry'  AND account_move.state = 'posted' AND  account_move_line.account_id=account_account.id AND
                             account_account.internal_group='income'
                              AND to_char(DATE(NOW()), 'MM') = to_char(account_move_line.date, 'MM')
                              ''')
        record = self._cr.dictfetchall()
        return record

    # function to get total income this month

    @api.model
    def month_income_this_month(self, *post):
        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select sum(debit) as debit, sum(credit) as credit from account_account, account_move_line where
                            account_move_line.account_id = account_account.id AND account_account.internal_group = 'income'
                           AND %s
                           AND Extract(month FROM account_move_line.date) = Extract(month FROM DATE(NOW())) 
                           AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW())) 
                           AND account_move_line.company_id in ''' + str(tuple(company_id)) + ''' 

                                 ''') % (states_arg))
        record = self._cr.dictfetchall()
        return record

    @api.model
    def profit_income_this_month(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select sum(debit) - sum(credit) as profit, account_account.internal_group from  account_account, account_move_line where 
                                  
                                    account_move_line.account_id = account_account.id AND
                                    %s AND
                                    (account_account.internal_group = 'income' or    
                                    account_account.internal_group = 'expense' ) 
                                    AND Extract(month FROM account_move_line.date) = Extract(month FROM DATE(NOW())) 
                                    AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW()))   
                                    AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''        
                                    group by internal_group 
                                     ''') % (states_arg))
        income = self._cr.dictfetchall()
        profit = [item['profit'] for item in income]
        internal_group = [item['internal_group'] for item in income]
        net_profit = True
        loss = True
        if profit and profit == 0:
            if (-profit[1]) > (profit[0]):
                net_profit = -profit[1] - profit[0]
            elif (profit[1]) > (profit[0]):
                net_profit = -profit[1] - profit[0]
            else:
                net_profit = -profit[1] - profit[0]

        return profit

    def get_current_company_value(self):

        cookies_cids = [int(r) for r in request.httprequest.cookies.get('cids').split(",")] \
            if request.httprequest.cookies.get('cids') \
            else [request.env.user.company_id.id]

        for company_id in cookies_cids:
            if company_id not in self.env.user.company_ids.ids:
                cookies_cids.remove(company_id)
        if not cookies_cids:
            cookies_cids = [self.env.company.id]
        if len(cookies_cids) == 1:
            cookies_cids.append(0)
        return cookies_cids

    @api.model
    def profit_income_this_year(self, *post):
        company_id = self.get_current_company_value()
        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute(('''select sum(debit) - sum(credit) as profit, account_account.internal_group from  account_account, account_move_line where 
                                        
                                         account_move_line.account_id = account_account.id AND
                                         %s AND
                                        (account_account.internal_group = 'income' or    
                                        account_account.internal_group = 'expense' )                                       
                                        AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW()))  
                                        AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''           
                                        group by internal_group 
                                         ''') % (states_arg))
        income = self._cr.dictfetchall()
        profit = [item['profit'] for item in income]
        internal_group = [item['internal_group'] for item in income]
        net_profit = True
        loss = True

        if profit and profit == 0:
            if (-profit[1]) > (profit[0]):
                net_profit = -profit[1] - profit[0]
            elif (profit[1]) > (profit[0]):
                net_profit = -profit[1] - profit[0]
            else:
                net_profit = -profit[1] - profit[0]

        return profit

    # function to get total income last month

    @api.model
    def month_income_last_month(self):

        one_month_ago = (datetime.now() - relativedelta(months=1)).month

        self._cr.execute('''
                            select sum(debit) as debit, sum(credit) as credit from  account_account, 
        account_move_line where 
         account_move_line.account_id = account_account.id 
        AND account_account.internal_group = 'income' AND 
        account_move_line.parent_state = 'posted'  
        AND Extract(month FROM account_move_line.date) = ''' + str(one_month_ago) + '''
        ''')

        record = self._cr.dictfetchall()

        return record

    # function to get total income this year

    @api.model
    def month_income_this_year(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute((''' select sum(debit) as debit, sum(credit) as credit from account_account, account_move_line where                           
                             account_move_line.account_id = account_account.id AND account_account.internal_group = 'income'
                             AND %s
                          AND Extract(YEAR FROM account_move_line.date) = Extract(YEAR FROM DATE(NOW())) 
                          AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                        ''') % (states_arg))
        record = self._cr.dictfetchall()
        return record

    # function to get total income last year

    @api.model
    def month_income_last_year(self):

        self._cr.execute(''' select sum(debit) as debit, sum(credit) as credit from  account_account, account_move_line where
                            account_move_line.parent_state = 'posted' 
                            AND  account_move_line.account_id = account_account.id AND account_account.internal_group = 'income'
                            AND Extract(YEAR FROM account_move_line.date) = Extract(YEAR FROM DATE(NOW())) - 1
                         ''')
        record = self._cr.dictfetchall()
        return record

    # function to get currency

    @api.model
    def get_currency(self):
        company_ids = self.get_current_company_value()
        if 0 in company_ids:
            company_ids.remove(0)
        current_company_id = company_ids[0]
        current_company = self.env['res.company'].browse(current_company_id)
        default = current_company.currency_id or self.env.ref('base.main_company').currency_id
        lang = self.env.user.lang
        if not lang:
            lang = 'en_US'
        lang = lang.replace("_", '-')
        currency = {'position': default.position, 'symbol': default.symbol, 'language': lang}
        return currency

    # function to get total expense

    @api.model
    def month_expense(self):

        self._cr.execute(''' select sum(debit) as debit , sum(credit) as credit from account_move, account_account,account_move_line
                            where account_move.move_type = 'entry'  AND account_move.state = 'posted' AND   account_move_line.account_id=account_account.id AND
                             account_account.internal_group='expense' 
                             AND to_char(DATE(NOW()), 'MM') = to_char(account_move_line.date, 'MM')
                             ''')
        record = self._cr.dictfetchall()
        return record

    # function to get total expense this month

    @api.model
    def month_expense_this_month(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute((''' select sum(debit) as debit, sum(credit) as credit from  account_account, account_move_line where 
                        
                            account_move_line.account_id = account_account.id AND account_account.internal_group = 'expense' AND  
                            %s                
                            AND Extract(month FROM account_move_line.date) = Extract(month FROM DATE(NOW()))
                            AND Extract(year FROM account_move_line.date) = Extract(year FROM DATE(NOW())) 
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''


                                 ''') % (states_arg))
        record = self._cr.dictfetchall()
        return record

    # function to get total expense this year

    @api.model
    def month_expense_this_year(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state in ('posted', 'draft')"""
        else:
            states_arg = """ parent_state = 'posted'"""

        self._cr.execute((''' select sum(debit) as debit, sum(credit) as credit from  account_account, account_move_line where
                        
                            account_move_line.account_id = account_account.id AND account_account.internal_group = 'expense' AND  
                            %s                         
                            AND Extract(YEAR FROM account_move_line.date) = Extract(YEAR FROM DATE(NOW())) 
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''



                            ''') % (states_arg))
        record = self._cr.dictfetchall()
        return record

    @api.model
    def bank_balance(self, *post):

        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ parent_state = 'posted'"""
        else:
            states_arg = """ parent_state in ('posted', 'draft')"""

        self._cr.execute((''' select account_account.name as name, sum(balance) as balance,
                            min(account_account.id) as id from account_move_line left join
                            account_account on account_account.id = account_move_line.account_id join
                            account_account_type on account_account_type.id = account_account.user_type_id
                            where account_account_type.name = 'Bank and Cash'
                            AND %s
                            AND account_move_line.company_id in ''' + str(tuple(company_id)) + '''
                            group by account_account.name
                                                   
                            ''') % (states_arg))

        record = self._cr.dictfetchall()

        banks = [item['name'] for item in record]

        banking = [item['balance'] for item in record]

        bank_ids = [item['id'] for item in record]

        records = {
            'banks': banks,
            'banking': banking,
            'bank_ids': bank_ids

        }
        return records
