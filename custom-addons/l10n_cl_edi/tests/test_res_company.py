# -*- coding: utf-8 -*-
import datetime

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import misc, os


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResCompany(TransactionCase):
    def setUp(self):
        super(TestResCompany, self).setUp()
        self.company_cl = self.env['res.company'].create({
            'country_id': self.env.ref('base.cl').id,
            'currency_id': self.env.ref('base.CLP').id,
            'name': 'Company CL',
        })
        self.certificate = self.env['l10n_cl.certificate'].sudo().create({
            'signature_filename': 'Not valid certificate',
            'subject_serial_number': '23841194-7',
            'signature_pass_phrase': 'asadadad',
            'private_key': misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'private_key_test.key')).read(),
            'certificate': misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'cert_test.cert')).read(),
            'cert_expiration': fields.Datetime.now() + datetime.timedelta(days=1),
        })

    def test_get_digital_signature_none(self):
        with self.assertRaises(
                UserError, msg="There is not a valid certificate for the company: %s" % self.company_cl.name):
            self.company_cl._get_digital_signature()

    def test_get_digital_signature_not_valid_signature(self):
        self.certificate.write({
            'cert_expiration': fields.Datetime.now() - datetime.timedelta(days=1),
            'company_id': self.company_cl.id
        })

        self.company_cl.write({'l10n_cl_certificate_ids': [(6, 0, [self.certificate.id])]})

        with self.assertRaises(
                UserError, msg="There is not a valid certificate for the company: %s" % self.company_cl.name):
            self.company_cl._get_digital_signature()

    def test_get_digital_signature_valid(self):
        self.certificate.write({'company_id': self.company_cl.id})
        self.company_cl.write({'l10n_cl_certificate_ids': [(6, 0, [self.certificate.id])]})

        self.assertEqual(self.company_cl._get_digital_signature(), self.certificate)

    def test_get_digital_signature_user_not_valid_certificate(self):
        user = self.env['res.users'].create({
            'name': 'Test Certificate User',
            'login': 'certificate_user',
            'groups_id': [(6, 0, self.env.user.groups_id.ids), (4, self.env.ref('account.group_account_user').id)],
        })
        user_certificate = self.env['l10n_cl.certificate'].create({
            'signature_filename': 'Not Valid User Certificate',
            'subject_serial_number': '23841194-7',
            'signature_pass_phrase': 'asadadad',
            'private_key': misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'private_key_test.key')).read(),
            'certificate': misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'cert_test.cert')).read(),
            'cert_expiration': fields.Datetime.now() - datetime.timedelta(days=1),
            'user_id': user.id
        })

        self.certificate.write({'company_id': self.company_cl.id})
        self.company_cl.write({'l10n_cl_certificate_ids': [(6, 0, [self.certificate.id, user_certificate.id])]})

        self.assertEqual(self.company_cl._get_digital_signature(user_id=user.id), self.certificate)

    def test_get_digital_signature_user_valid_certificate(self):
        user = self.env['res.users'].create({
            'name': 'Test Certificate User',
            'login': 'certificate_user',
            'groups_id': [(6, 0, self.env.user.groups_id.ids), (4, self.env.ref('account.group_account_user').id)],
        })
        user_certificate = self.env['l10n_cl.certificate'].create({
            'signature_filename': 'Valid User Certificate',
            'subject_serial_number': '23841194-7',
            'signature_pass_phrase': 'asadadad',
            'private_key': misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'private_key_test.key')).read(),
            'certificate': misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'cert_test.cert')).read(),
            'cert_expiration': fields.Datetime.now() + datetime.timedelta(days=1),
            'user_id': user.id
        })

        self.certificate.write({'cert_expiration': fields.Datetime.now() + datetime.timedelta(days=1)})
        self.company_cl.write({'l10n_cl_certificate_ids': [(6, 0, [self.certificate.id, user_certificate.id])]})

        self.assertEqual(self.company_cl._get_digital_signature(user_id=user.id), user_certificate)
