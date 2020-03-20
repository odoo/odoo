from odoo import fields
from odoo.tests import common, tagged
from odoo.sql_db import flush_env
import logging
import time
_logger = logging.getLogger(__name__)

ENTITIES = 1000
MSG = "Model %s, %i records, %s, time %.2f"

# for c/c
# t0 = time.time()
# model = self.env["product.product"]
# vals_list = [
#     dict() for i in range(ENTITIES)
# ]
# model.create(vals_list)
# _logger.warning(MSG, model._name, ENTITIES, "BATCH", time.time() - t0)

def product_vals():
    vals_list = [{
        "name": "P%i"%i,
        "type": "product",
    } for i in range(ENTITIES)]
    vals_list += [{
        "name": "P%i"%i,
        "type": "consu",
    } for i in range(ENTITIES)]
    return vals_list

def so_vals():
    return [{
        "partner_id": 1,
        "user_id": 1,
        "order_line": [
            (0, 0, {"product_id": 5}),
            (0, 0, {"product_id": 7}),
            (0, 0, {"display_type": "line_note", "name": "NOTE"})
        ]
    } for i in range(ENTITIES)]

def sol_vals():
    return [{
        "partner_id": 1,
        "user_id": 1,
        "order_line": [
            (0, 0, {"product_id": 8, "product_uom_qty": i}) for i in range(ENTITIES)
        ]
    }]

def am_vals(journal_id):
    # def create_move(name, amount, amount_currency, currency_id):
    # debit_line_vals = {
    #     'name': name,
    #     'debit': amount > 0 and amount or 0.0,
    #     'credit': amount < 0 and -amount or 0.0,
    #     'account_id': self.account_rcv.id,
    #     'amount_currency': amount_currency,
    #     'currency_id': currency_id,
    # }
    # credit_line_vals = debit_line_vals.copy()
    # credit_line_vals['debit'] = debit_line_vals['credit']
    # credit_line_vals['credit'] = debit_line_vals['debit']
    # credit_line_vals['account_id'] = self.account_rsa.id
    # credit_line_vals['amount_currency'] = -debit_line_vals['amount_currency']
    # vals = {
    #     'journal_id': self.bank_journal_euro.id,
    #     'line_ids': [(0,0, debit_line_vals), (0, 0, credit_line_vals)]
    # }
    return [{
        'journal_id': journal_id,
        'invoice_line_ids': [(0,0, {
            'name': "name",
            'debit': amount,
            'credit': -amount,
            'currency_id': 2,
        })],
    } for amount in range(ENTITIES)]

# def aml_vals(journal_id):
#     return {
#         # thinking a journal_id is necessary
#         'partner_id': 1,
#         'journal_id': journal_id,
#         'invoice_line_ids': [(0, 0, {
#             'name': 'test',
#             'quantity': 1,
#             'price_unit': i,
#             'credit': i,
#         }) for i in range(ENTITIES)]
#     }


class TestPERF(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.bank_journal_euro = self.env['account.journal'].create(
            {'name': 'Bank', 'type': 'bank', 'code': 'BNK67'}
        )

    # def test_1product_batch(self):
    #     model = self.env["product.product"]
    #     vals_list = product_vals()
    #     t0 = time.time()
    #     model.create(vals_list)
    #     t1 = time.time()
    #     _logger.warning(MSG, model._name, ENTITIES, "BATCH", t1 - t0)
    #     flush_env(model.env.cr)
    #     _logger.warning(MSG, model._name, ENTITIES, "FLUSH", time.time() - t1)

    # def test_2product_unique(self):
    #     model = self.env["product.product"]
    #     vals = product_vals()
    #     t0 = time.time()
    #     for val in vals:
    #         model.create(val)
    #         flush_env(model.env.cr)
    #     _logger.warning(MSG, model._name, ENTITIES, "UNIQUE", time.time() - t0)

    def test_3sale_order_batch(self):
        model = self.env["sale.order"]
        vals_list = so_vals()
        t0 = time.time()
        model.create(vals_list)
        t1 = time.time()
        _logger.warning(MSG, model._name, ENTITIES, "BATCH", t1 - t0)
        flush_env(model.env.cr)
        _logger.warning(MSG, model._name, ENTITIES, "FLUSH", time.time() - t1)

    # def test_4sale_order_line_batch(self):
    #     model = self.env["sale.order"]
    #     vals_list = sol_vals()
    #     t0 = time.time()
    #     model.create(vals_list)
    #     t1 = time.time()
    #     _logger.warning(MSG, "sale.order.line", ENTITIES, "BATCH", t1 - t0)
    #     flush_env(model.env.cr)
    #     _logger.warning(MSG, "sale.order.line", ENTITIES, "FLUSH", time.time() - t1)

    # def test_5account_move_batch(self):
    #     model = self.env["account.move"]
    #     vals_list = am_vals(self.bank_journal_euro.id)
    #     t0 = time.time()
    #     model.create(vals_list)
    #     t1 = time.time()
    #     _logger.warning(MSG, model._name, ENTITIES, "BATCH", t1 - t0)
    #     flush_env(model.env.cr)
    #     _logger.warning(MSG, model._name, ENTITIES, "FLUSH", time.time() - t1)

    # def test_account_move_line_batch(self):
    #     model = self.env["account.move"]
    #     vals_list = aml_vals(self.bank_journal_euro.id)
    #     t0 = time.time()
    #     model.create(vals_list)
    #     _logger.warning(MSG, "account.move.line", ENTITIES, "BATCH", time.time() - t0)
    #     flush_env(model.env.cr)
    #     _logger.warning(MSG, "account.move.line", ENTITIES, "FLUSH", time.time() - t0)

    # c/c II
    # t0 = time.time()
    # model = self.env["product.product"]
    # for i in range(ENTITIES):
    #     model.create(dict())
    # _logger.warning(MSG, model._name, ENTITIES, "UNIQUE", time.time() - t0)

    # def test_4sale_order_unique(self):
    #     model = self.env["sale.order"]
    #     vals = so_vals()
    #     t0 = time.time()
    #     for val in vals:
    #         model.create(val)
    #         flush_env(model.env.cr)
    #     _logger.warning(MSG, model._name, ENTITIES, "UNIQUE", time.time() - t0)

    # # def test_sale_order_line_unique(self):
    # #     t0 = time.time()
    # #     model = self.env["product.product"]
    # #     for i in range(ENTITIES):
    # #         model.create(dict())
    # #     _logger.warning(MSG, model._name, ENTITIES, "UNIQUE", time.time() - t0)

    # def test_6account_move_unique(self):
    #     model = self.env["account.move"]
    #     vals = am_vals(self.bank_journal_euro.id)
    #     t0 = time.time()
    #     for val in vals:
    #         model.create(val)
    #         flush_env(model.env.cr)
    #     _logger.warning(MSG, model._name, ENTITIES, "UNIQUE", time.time() - t0)

    # def test_account_move_line_unique(self):
    #     t0 = time.time()
    #     model = self.env["account.move"]
    #     for i in range(ENTITIES):
    #         model.create(dict())
    #     _logger.warning(MSG, model._name, ENTITIES, "UNIQUE", time.time() - t0)