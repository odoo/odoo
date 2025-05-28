# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Akhil Ashok (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import base64
import codecs
import openpyxl
import os
from datetime import datetime
from io import BytesIO
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from ofxparse import OfxParser
from qifparse.parser import QifParser


class ImportBankStatement(models.TransientModel):
    """ A class to import files as bank statement """
    _name = "import.bank.statement"
    _description = "Import button"
    _rec_name = "file_name"

    attachment = fields.Binary(string="File", required=True,
                               help="Choose the file to import")
    file_name = fields.Char(string="File Name", help="Name of the file")
    journal_id = fields.Many2one('account.journal', string="Journal ID",
                                 help="Journal in which the file importing")

    def action_statement_import(self):
        """Function to import csv, xlsx, ofx and qif file format"""
        split_tup = os.path.splitext(self.file_name)
        if split_tup[1] == '.csv' or split_tup[1] == '.xlsx' or split_tup[
            1] == '.ofx' or split_tup[1] == '.qif':
            if split_tup[1] == '.csv':
                # Reading csv file
                try:
                    file = base64.b64decode(self.attachment)
                    file_string = file.decode('utf-8')
                    file_string = file_string.split('\n')
                except:
                    raise ValidationError(_("Choose correct file"))
                # Skipping the first line
                firstline = True
                for file_item in file_string:
                    if firstline:
                        firstline = False
                        continue
                    # Reading the content from csv file
                    if file_item.split(',') != ['']:
                        if file_item.split(',')[0] and file_item.split(',')[1] \
                                and file_item.split(',')[4]:
                            date_obj = str(fields.date.today()) if not \
                                file_item.split(',')[3] else \
                                file_item.split(',')[
                                    3]
                            transaction_date = datetime.strptime(date_obj,
                                                                 "%Y-%m-%d")
                            partner = self.env['res.partner'].search(
                                [('name', '=', file_item.split(',')[4])])
                            # Creating a record in account.bank.statement model
                            if partner:
                                statement = self.env[
                                    'account.bank.statement'].create({
                                     'name': file_item.split(',')[0],
                                     'line_ids': [
                                        (0, 0, {
                                            'date': transaction_date,
                                            'payment_ref': 'csv file',
                                            'partner_id': partner.id,
                                            'journal_id': self.journal_id.id,
                                            'amount': file_item.split(',')[1],
                                            'amount_currency':
                                                file_item.split(',')[2],
                                        }),
                                    ],
                                })
                            else:
                                raise ValidationError(_("Partner not exist"))
                        else:
                            if not file_item.split(',')[0]:
                                raise ValidationError(
                                    _("Account name is not set"))
                            elif not file_item.split(',')[1]:
                                raise ValidationError(
                                    _("Amount is not set"))
                            elif not file_item.split(',')[4]:
                                date_obj = str(fields.date.today()) if not \
                                    file_item.split(',')[3] else \
                                    file_item.split(',')[
                                        3]
                                transaction_date = datetime.strptime(date_obj,
                                                                     "%Y-%m-%d")
                                # Creating a record in account.bank.statement model
                                statement = self.env[
                                    'account.bank.statement'].create({
                                    'name': file_item.split(',')[0],
                                    'line_ids': [
                                        (0, 0, {
                                            'date': transaction_date,
                                            'payment_ref': 'csv file',
                                            'journal_id': self.journal_id.id,
                                            'amount': file_item.split(',')[
                                                1],
                                            'amount_currency':
                                                file_item.split(',')[2],
                                        }),
                                    ],
                                })
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Statements',
                    'view_mode': 'list',
                    'res_model': 'account.bank.statement',
                    'res_id': statement.id,
                }
            elif split_tup[1] == '.xlsx':
                # Reading xlsx file
                try:
                    order = openpyxl.load_workbook(
                        filename=BytesIO(base64.b64decode(self.attachment)))
                    xl_order = order.active
                except:
                    raise ValidationError(_("Choose correct file"))
                for record in xl_order.iter_rows(min_row=2, max_row=None,
                                                 min_col=None,
                                                 max_col=None,
                                                 values_only=True):
                    line = list(record)
                    # Reading the content from file
                    if line[0] and line[1] and line[3]:
                        partner = self.env['res.partner'].search(
                            [('name', '=', line[3])])
                        date_obj = fields.date.today() if not line[2] else \
                            line[2].date()
                        # Creating record
                        if partner:
                            statement = self.env[
                                'account.bank.statement'].create({
                                 'name': line[0],
                                 'line_ids': [
                                    (0, 0, {
                                        'date': date_obj,
                                        'payment_ref': 'xlsx file',
                                        'partner_id': partner.id,
                                        'journal_id': self.journal_id.id,
                                        'amount': line[1],
                                    }),
                                 ],
                                })
                        else:
                            raise ValidationError(_("Partner not exist"))
                    else:
                        if not line[0]:
                            raise ValidationError(
                                _("Account name is not set"))
                        elif not line[1]:
                            raise ValidationError(
                                _("Amount is not set"))
                        elif not line[3]:
                            date_obj = fields.date.today() if not line[2] else \
                                line[2].date()
                            # Creating record
                            statement = self.env[
                                'account.bank.statement'].create({
                                'name': line[0],
                                'line_ids': [
                                    (0, 0, {
                                        'date': date_obj,
                                        'payment_ref': 'xlsx file',
                                        'journal_id': self.journal_id.id,
                                        'amount': line[1],
                                    }),
                                ],
                            })
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Statements',
                    'view_mode': 'list',
                    'res_model': 'account.bank.statement',
                    'res_id': statement.id,
                }
            elif split_tup[1] == '.ofx':
                # Searching the path of the file
                file_attachment = self.env["ir.attachment"].search(
                    ['|', ('res_field', '!=', False),
                     ('res_field', '=', False),
                     ('res_id', '=', self.id),
                     ('res_model', '=', 'import.bank.statement')],
                    limit=1)
                file_path = file_attachment._full_path(
                    file_attachment.store_fname)
                # Parsing the file
                try:
                    with codecs.open(file_path) as fileobj:
                        ofx_file = OfxParser.parse(fileobj)
                except:
                    raise ValidationError(_("Wrong file format"))
                if not ofx_file.account:
                    raise ValidationError(
                        _("No account information found in OFX file."))
                if not ofx_file.account.statement:
                    raise ValidationError(
                        _("No statement information found in OFX file."))
                statement_list = []
                # Reading the content from file
                for transaction in ofx_file.account.statement.transactions:
                    if transaction.type == "debit" and transaction.amount != 0:
                        payee = transaction.payee
                        amount = transaction.amount
                        date = transaction.date
                        if not date:
                            date = fields.date.today()
                        partner = self.env['res.partner'].search(
                            [('name', '=', payee)])
                        if partner:
                            statement_list.append([partner.id, amount, date])
                        else:
                            raise ValidationError(_("Partner not exist"))
                    if transaction.type == "credit" and transaction.amount != 0:
                        payee = transaction.payee
                        amount = transaction.amount
                        date = transaction.date
                        if not date:
                            date = fields.date.today()
                        partner = self.env['res.partner'].search(
                            [('name', '=', payee)])
                        if partner:
                            statement_list.append([partner.id, amount, date])
                        else:
                            raise ValidationError(_("Partner not exist"))
                # Creating record
                if statement_list:
                    for item in statement_list:
                        statement = self.env['account.bank.statement'].create({
                            'name': ofx_file.account.routing_number,
                            'line_ids': [
                                (0, 0, {
                                    'date': item[2],
                                    'payment_ref': 'ofx file',
                                    'partner_id': item[0],
                                    'journal_id': self.journal_id.id,
                                    'amount': item[1],
                                }),
                            ],
                        })
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Statements',
                        'view_mode': 'list',
                        'res_model': 'account.bank.statement',
                        'res_id': statement.id,
                    }
                else:
                    raise ValidationError(_("There is no data to import"))
            elif split_tup[1] == '.qif':
                # Searching the path of qif file
                file_attachment = self.env["ir.attachment"].search(
                    ['|', ('res_field', '!=', False),
                     ('res_field', '=', False),
                     ('res_id', '=', self.id),
                     ('res_model', '=', 'import.bank.statement')],
                    limit=1)
                file_path = file_attachment._full_path(
                    file_attachment.store_fname)
                # Parsing the qif file
                try:
                    parser = QifParser()
                    with open(file_path, 'r') as qiffile:
                        qif = parser.parse(qiffile)
                except:
                    raise ValidationError(_("Wrong file format"))
                file_string = str(qif)
                file_item = file_string.split('^')
                file_item[-1] = file_item[-1].rstrip('\n')
                if file_item[-1] == '':
                    file_item.pop()
                statement_list = []
                for item in file_item:
                    if not item.startswith('!Type:Bank'):
                        item = '!Type:Bank' + item
                    data = item.split('\n')
                    # Reading the file content
                    date_entry = data[1][1:]
                    amount = float(data[2][1:])
                    payee = data[3][1:]
                    if amount and payee:
                        if not date_entry:
                            date_entry = str(fields.date.today())
                        date_object = datetime.strptime(date_entry, '%d/%m/%Y')
                        date = date_object.strftime('%Y-%m-%d')
                        statement_list.append([payee, amount, date])
                    else:
                        if not amount:
                            raise ValidationError(_("Amount is not set"))
                        elif not payee:
                            raise ValidationError(_("Payee is not set"))
                # Creating record
                if statement_list:
                    for item in statement_list:
                        statement = self.env['account.bank.statement'].create({
                            'name': item[0],
                            'line_ids': [
                                (0, 0, {
                                    'date': item[2],
                                    'payment_ref': 'qif file',
                                    'journal_id': self.journal_id.id,
                                    'amount': item[1],
                                }),
                            ],
                        })
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Statements',
                        'view_mode': 'list',
                        'res_model': 'account.bank.statement',
                        'res_id': statement.id,
                    }
        else:
            raise ValidationError(_("Choose correct file"))
