from odoo import http
from odoo.http import request

from datetime import datetime


class AccountBalanceController(http.Controller):

    @http.route('/get_balance_sum', type='json', methods=['POST'], auth='public', csrf=False, cors='*')
    def balance_sum(self, db, login, password, start_date=None, end_date=None):
        request.session.logout()
        request.session.authenticate(db, login, password)

        # Convert the input date strings to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Fetch move lines from the 'account.move.line' model
        move_lines = request.env['account.move.line'].search([])

        account_data = {}

        for move_line in move_lines:
            account_id = move_line.account_id.id
            balance = move_line.balance
            account_root_id = move_line.account_root_id.id
            account_date = datetime.combine(move_line.date, datetime.min.time())  # Convert to datetime object

            # Check if the account_date is within the specified date range
            if start_date <= account_date <= end_date:
                # Fetch account name from the 'account.account' model
                account_name = request.env['account.account'].browse(account_id).name

                if account_id not in account_data:
                    account_data[account_id] = {
                        'account_id': account_id,
                        'account_name': account_name,
                        'balance': balance,
                        'account_root_id': account_root_id,
                        'movement_date': account_date.strftime('%Y-%m-%d'),
                    }
                else:
                    account_data[account_id]['balance'] += balance

        # Convert the dictionary of account balances to a list
        account_data_list = list(account_data.values())

        # Add the total balance to the response
        total_balance = sum(entry['balance'] for entry in account_data_list)

        data = {
            'status': 200,
            'response': account_data_list,
            'total_balance': total_balance,
            'message': 'Success',
        }
        return data

    @http.route('/get_balance_test', type='json', auth='none', csrf=False, cors='*')
    def balance_test(self, db, login, password, start_date=None, end_date=None):
        request.session.logout()
        request.session.authenticate(db, login, password)

        # Convert the input date strings to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Fetch move lines from the 'account.move.line' model
        move_lines = request.env['account.move.line'].search([])

        account_data = {}

        for move_line in move_lines:
            account_id = move_line.account_id.id
            balance = move_line.balance
            account_root_id = move_line.account_root_id.id
            account_date = datetime.combine(move_line.date, datetime.min.time())  # Convert to datetime object

            # Check if the account_date is within the specified date range
            if start_date <= account_date <= end_date:
                # Fetch account name from the 'account.account' model
                account_name = request.env['account.account'].browse(account_id).name

                if account_id not in account_data:
                    account_data[account_id] = {
                        'account_id': account_id,
                        'account_name': account_name,
                        'balance': balance,
                        'account_root_id': account_root_id,
                        'movement_date': account_date.strftime('%Y-%m-%d'),
                    }
                else:
                    account_data[account_id]['balance'] += balance

        # Convert the dictionary of account balances to a list
        account_data_list = list(account_data.values())

        # Add the total balance to the response
        total_balance = sum(entry['balance'] for entry in account_data_list)

        data = {
            'status': 200,
            'response': account_data_list,
            'total_balance': total_balance,
            'message': 'Success',
        }
        return data

    @http.route('/get_balance_test', type='json', auth='none', csrf=False, cors='*')
    def balance_test(self, db, login, password):
        request.session.logout()
        request.session.authenticate(db, login, password)

        # Fetch move lines from the 'account.move.line' model
        move_lines = request.env['account.move.line'].search([])

        account_data = {}

        for move_line in move_lines:
            account_id = move_line.account_id.id
            balance = move_line.balance
            account_root_id = move_line.account_root_id.id
            account_date = datetime.combine(move_line.date, datetime.min.time())  # Convert to datetime object

            # Fetch account name from the 'account.account' model
            account_name = request.env['account.account'].browse(account_id).name

            if account_id not in account_data:
                account_data[account_id] = {
                    'account_id': account_id,
                    'account_name': account_name,
                    'balance': balance,
                    'account_root_id': account_root_id,
                    'movement_date': account_date.strftime('%Y-%m-%d'),
                }
            else:
                account_data[account_id]['balance'] += balance

        # Convert the dictionary of account balances to a list
        account_data_list = list(account_data.values())

        # Add the total balance to the response
        total_balance = sum(entry['balance'] for entry in account_data_list)

        data = {
            'status': 200,
            'response': account_data_list,
            'total_balance': total_balance,
            'message': 'Success',
        }
        return data

















