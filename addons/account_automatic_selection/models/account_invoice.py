# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

import numpy
import sklearn
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import json
from odoo.addons.account_automatic_selection.data.stop_words import stop_words as stop_words_data

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    _count_vectorizer = None
    _multinomialNB = None
    _last_quantity_update = 0

    @api.onchange('name')
    def _onchange_name(self):
        if not self.name:
            return
        type_to_search = []
        account = []
        if self.invoice_id.type in ["in_invoice", "out_refund"]:
            type_to_search = ["in_invoice", "out_refund"]
            accounts = self.env["account.account"].search([('user_type_id.name', 'in', ['Income', 'Other Income'])])
        elif self.invoice_id.type in ["out_invoice", "in_refund"]:
            type_to_search = ["out_invoice", "in_refund"]
            accounts = self.env["account.account"].search([('user_type_id.name', 'in', ['Expenses', 'Cost of Revenue', 'Fixed Assets'])])
        invoice_lines = self.env['account.invoice.line'].search([('invoice_id.type', "in", type_to_search), ('invoice_id.state', 'in', ('open','paid'))])

        account_descr = [(x['account_id'], x['name']) for x in invoice_lines]
        for account in  accounts:
            account_descr.append((account,account.name))

        labels = [x[0].id for x in account_descr]
        names = [x[1] for x in account_descr]

        if names:
            #create predicting models
            if not AccountInvoiceLine._count_vectorizer or \
            AccountInvoiceLine.last_quantity_update < len(names) - 10 or len(names) < 100:
                stop_words = self.load_stop_words()
                AccountInvoiceLine._count_vectorizer = CountVectorizer(strip_accents='unicode', stop_words=stop_words)
                AccountInvoiceLine.last_quantity_update = len(names)
                features = AccountInvoiceLine._count_vectorizer.fit_transform(names).toarray()
                clf = MultinomialNB(alpha=1.0e-10)
                clf.fit(features, numpy.array(labels))

            # Predicting

            predict = numpy.array(AccountInvoiceLine._count_vectorizer.transform([self.name]).toarray())
            proba  = clf.predict_proba(predict)
            max_proba = max(proba[0])
            index_max = numpy.where(proba[0] == max_proba)
            account_id = clf.classes_[index_max]
            if max_proba > 0.6 and not self.account_id:
                #as max_proba is > 0.5, we are sure that len(account_id) == 1
                acc = self.env["account.account"].search([('id', '=', account_id[0])])
                if acc.exists():
                    self.account_id = acc

    def load_stop_words(self):
        stop_words = []
        stop_words = stop_words_data["en"]
        for lang in stop_words_data:
            if lang in self.env.user.partner_id.lang and lang != "en":
                for word in stop_words_data[lang]:
                    stop_words.append(word)

        return stop_words
