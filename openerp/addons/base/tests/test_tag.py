# -*- coding: utf-8 -*-
import openerp
from openerp.tests import common
from openerp.exceptions import ValidationError

class TestUniqueAccentTag(common.TransactionCase):
    def test_00_tag_constraint(self):
        ResPartnerCategory = self.env['res.partner.category']
        ResPartnerCategory.create({'name':'test'})
        # same category name should not allowed 
        self.assertRaises(ValidationError, ResPartnerCategory.create, {'name':'Test'})
        # same category name (case insencitive) should not allowed
        self.assertRaises(ValidationError, ResPartnerCategory.create, {'name':'test'})
        has_unaccent = openerp.modules.db.has_unaccent(self.env.cr)
        # if unaccent in postgress and option --unaccent given than unique is maintain in accent chars. 
        if openerp.tools.config['unaccent'] and has_unaccent:
            self.assertRaises(ValidationError, ResPartnerCategory.create, {'name':'Tést'})
        else:
            ResPartnerCategory.create({'name':'Tést'})