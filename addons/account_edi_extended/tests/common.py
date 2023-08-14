# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from contextlib import contextmanager
from unittest.mock import patch
import base64

# TODO for the test to work, we need a chart template (COA) but we don't have any and don't want to add dependency (create empty coa ?)


def _generate_mocked_needs_web_services(needs_web_services):
    return lambda edi_format: needs_web_services


def _generate_mocked_support_batching(support_batching):
    return lambda edi_format, move, state, company: support_batching


def _mocked_get_batch_key(edi_format, move, state):
    return ()


def _mocked_check_move_configuration_success(edi_format, move):
    return []


def _mocked_check_move_configuration_fail(edi_format, move):
    return ['Fake error (mocked)']


def _mocked_post(edi_format, invoices, test_mode):
    res = {}
    for invoice in invoices:
        attachment = edi_format.env['ir.attachment'].create({
            'name': 'mock_simple.xml',
            'datas': base64.encodebytes(b"<?xml version='1.0' encoding='UTF-8'?><Invoice/>"),
            'mimetype': 'application/xml'
        })
        res[invoice] = {'attachment': attachment}
    return res


def _mocked_post_two_steps(edi_format, invoices, test_mode):
    # For this test, we use the field ref to know if the first step is already done or not.
    # Typically, a technical field for the reference of the upload to the web-service will
    # be saved on the invoice.
    invoices_no_ref = invoices.filtered(lambda i: not i.ref)
    if len(invoices_no_ref) == len(invoices):  # first step
        invoices_no_ref.ref = 'test_ref'
        return {invoice: {} for invoice in invoices}
    elif len(invoices_no_ref) == 0:  # second step
        res = {}
        for invoice in invoices:
            attachment = edi_format.env['ir.attachment'].create({
                'name': 'mock_simple.xml',
                'datas': base64.encodebytes(b"<?xml version='1.0' encoding='UTF-8'?><Invoice/>"),
                'mimetype': 'application/xml'
            })
            res[invoice] = {'attachment': attachment}
        return res
    else:
        raise ValueError('wrong use of "_mocked_post_two_steps"')


def _mocked_cancel_success(edi_format, invoices, test_mode):
    return {invoice: {'success': True} for invoice in invoices}


def _mocked_cancel_failed(edi_format, invoices, test_mode):
    return {invoice: {'error': 'Faked error (mocked)'} for invoice in invoices}


class AccountEdiExtendedTestCommon(AccountEdiTestCommon):

    @contextmanager
    def mock_edi(self,
                 _is_required_for_invoice_method=lambda edi_format, invoice: True,
                 _is_required_for_payment_method=lambda edi_format, invoice: True,
                 _support_batching_method=_generate_mocked_support_batching(False),
                 _get_batch_key_method=_mocked_get_batch_key,
                 _needs_web_services_method=_generate_mocked_needs_web_services(False),
                 _check_move_configuration_method=_mocked_check_move_configuration_success,
                 _post_invoice_edi_method=_mocked_post,
                 _cancel_invoice_edi_method=_mocked_cancel_success,
                 _post_payment_edi_method=_mocked_post,
                 _cancel_payment_edi_method=_mocked_cancel_success,
                 ):

        try:
            with patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._is_required_for_invoice',
                       new=_is_required_for_invoice_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._is_required_for_payment',
                       new=_is_required_for_payment_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._needs_web_services',
                       new=_needs_web_services_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._support_batching',
                       new=_support_batching_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._get_batch_key',
                       new=_get_batch_key_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._check_move_configuration',
                       new=_check_move_configuration_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._post_invoice_edi',
                       new=_post_invoice_edi_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._cancel_invoice_edi',
                       new=_cancel_invoice_edi_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._post_payment_edi',
                       new=_post_payment_edi_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._cancel_payment_edi',
                       new=_cancel_payment_edi_method):

                yield
        finally:
            pass
