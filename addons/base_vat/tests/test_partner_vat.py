# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os

from odoo.tests import common

_logger = logging.getLogger(__name__)


class TestPartnerVat(common.TransactionCase):
    def setUp(self):
        super(TestPartnerVat, self).setUp()
        self.partner = self.env.ref('base.res_partner_1')
        self.partner.is_company = True
        self.partner.country_id = None
        self.partner.vat = None
        self.env.user.company_id.vat_check_vies = None
        self.test_dir = os.path.dirname(os.path.realpath(__file__))

    def check_vat_valids(self, vat_valids, country, prefix=None):
        if prefix is None:
            prefix = ''
        self.partner.country_id = country
        for vat_valid in vat_valids:
            # Faster way of change the vat without database access
            self.partner._cache['vat'] = prefix + vat_valid
            try:
                self.partner.check_vat()
            except UnicodeEncodeError:
                _logger.info("Unicode error value # %d",
                             vat_valids.index(vat_valid) + 1)

    def test_partner_vat_mx_valids(self):
        vat_valids = []
        fname = os.path.join(self.test_dir, "vat_mx_valid_examples.txt")
        with open(fname, "r") as fmx:
            for line in fmx:
                vat_valids.append(line.rstrip('\n').decode('UTF-8'))
        self.check_vat_valids(vat_valids, self.env.ref('base.mx'))
