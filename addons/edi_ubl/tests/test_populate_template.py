# -*- coding: utf-8 -*-

from lxml import etree
from jinja2 import Template
from odoo.tests.common import TransactionCase
from odoo import tools

class TestPopulateTemplate(TransactionCase):

    def test_populate_template(self):
        pass
        # self.bbb = '123'
        # t = Template("{{ unicode(value) }}")
        # output = t.render({'value': 1235})
        # print('\n' + str(output) + '\n')
        # base_bust = self.env['base.bust'].create({})
        # template = self.env['bust.template'].create({
        #     'path': 'base_bust_ubl/data',
        #     'name': 'invoice_ubl_2_1_template',
        #     })
        # template_root = base_bust.create_root_node_from_template(template)
        # print(etree.tostring(template_root, pretty_print=True, encoding='UTF-8', xml_declaration=True))
