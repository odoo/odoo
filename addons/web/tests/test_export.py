# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
import json
from odoo import http
from odoo.tests import common, new_test_user
from odoo.addons.web.controllers.main import ExportXlsxWriter


class TestExport(common.HttpCase):

    def setUp(self):
        super().setUp()

        # Archive demo partners
        self.env['res.users'].search([]).active = False
        self.env['res.partner'].search([]).active = False
        new_test_user(self.env, login='fef', password='pwd')
        self.authenticate('fef', 'pwd')

        self.env['res.partner'].create([{
            'name': 'partner 1',
            'comment': 'yop',
            'website': 'yop.com',
            'credit_limit': 0,
        },{
            'name': 'partner 2',
            'comment': 'yop',
            'website': 'blop.com',
            'credit_limit': 3,
        },{
            'name': 'partner 3',
            'comment': 'yop',
            'website': 'blop.com',
            'credit_limit': 1,
        }, {
            'name': 'partner 4',
            'comment': 'blop',
            'website': 'blop.com',
            'credit_limit': 2,
        }])

        self.worksheet = {}  # mock worksheet

        self.default_params = {
            'domain': [],
            'fields': [{
                'label': "Partner name",
                'name': 'name',
            }, {
                'label': "Comment",
                'name': "comment",
            }, {
                'label': 'Website',
                'name': 'website',
            }],
            'groupby': [],
            'ids': False,
            'import_compat': False,
            'model': 'res.partner',
        }

    def mock_write(self, row, column, value, style=None):
        self.worksheet[row, column] = value

    def test_grouped_list_export(self):

        with patch.object(ExportXlsxWriter, 'write', self.mock_write):
            self.default_params['groupby'] = ['comment', 'website']
            params = dict(self.default_params, **{
                'groupby': ['comment', 'website'],
                'fields': [*self.default_params['fields'], {'label': "Credit Limit", 'name': 'credit_limit'}]
            })
            self.url_open('/web/export/xlsx', data={
                'data': json.dumps(params),
                'token': 'dummy',
                'csrf_token': http.WebRequest.csrf_token(self),
            })

        # Main header
        self.assertEqual(self.worksheet[0, 0], "Partner name", "It should display the list header")
        self.assertEqual(self.worksheet[0, 1], "Comment", "It should display the list header")
        self.assertEqual(self.worksheet[0, 2], "Website", "It should display the list header")
        self.assertEqual(self.worksheet[0, 3], "Credit Limit", "It should display the list header")

        # Header: Group Comment=blop
        self.assertEqual(self.worksheet[1, 0], "blop (1)", "It should display the group header")
        self.assertEqual(self.worksheet[1, 3], 2, "It should display the aggregated value")

        # Header: Group Comment=blop > Website=http://blop.com
        self.assertEqual(self.worksheet[2, 0], "    http://blop.com (1)", "It should display the group header")
        self.assertEqual(self.worksheet[2, 3], 2, "It should display the aggregated value")

        # Data: Group Comment=blop > Website=http://blop.com
        self.assertEqual(self.worksheet[3, 0], "partner 4")
        self.assertEqual(self.worksheet[3, 1], "blop")
        self.assertEqual(self.worksheet[3, 2], "http://blop.com")
        self.assertEqual(self.worksheet[3, 3], 2)

        # Header: Group Comment=yop
        self.assertEqual(self.worksheet[4, 0], "yop (3)", "It should display the group header")
        self.assertEqual(self.worksheet[4, 3], 4, "It should display the aggregated value")

        # Header: Group Comment=yop > Website=http://blop.com
        self.assertEqual(self.worksheet[5, 0], "    http://blop.com (2)", "It should display the group header")
        self.assertEqual(self.worksheet[5, 3], 4, "It should display the aggregated value")

        # Data: Group Comment=yop > Website=http://blop.com
        self.assertEqual(self.worksheet[6, 0], "partner 2")
        self.assertEqual(self.worksheet[6, 1], "yop")
        self.assertEqual(self.worksheet[6, 2], "http://blop.com")
        self.assertEqual(self.worksheet[6, 3], 3)

        self.assertEqual(self.worksheet[7, 0], "partner 3")
        self.assertEqual(self.worksheet[7, 1], "yop")
        self.assertEqual(self.worksheet[7, 2], "http://blop.com")
        self.assertEqual(self.worksheet[7, 3], 1)

        # Header: Group Comment=yop > Website=http://yop.com
        self.assertEqual(self.worksheet[8, 0], "    http://yop.com (1)", "It should display the group header")
        self.assertEqual(self.worksheet[8, 3], '', "It should not have any aggregated value")

        # Data: Group Comment=yop > Website=http://yop.com
        self.assertEqual(self.worksheet[9, 0], "partner 1")
        self.assertEqual(self.worksheet[9, 1], "yop")
        self.assertEqual(self.worksheet[9, 2], "http://yop.com")
        self.assertEqual(self.worksheet[9, 3], 0)

        # Header: Group Comment=False
        self.assertEqual(self.worksheet[10, 0], "Undefined (1)", "It should display the group header")
        self.assertEqual(self.worksheet[10, 3], '', "It should not have any aggregated value")

        # Header: Group Comment=False > Website=False
        self.assertEqual(self.worksheet[11, 0], "    Undefined (1)", "It should display the group header")
        self.assertEqual(self.worksheet[11, 3], '', "It should not have any aggregated value")

        # Data: Group Comment=False > Website=False
        self.assertEqual(self.worksheet[12, 0], "fef (base.group_user)")
        self.assertEqual(self.worksheet[12, 1], "")
        self.assertEqual(self.worksheet[12, 2], "")
        self.assertEqual(self.worksheet[12, 3], 0)

    def test_list_export(self):

        with patch.object(ExportXlsxWriter, 'write', self.mock_write):
            self.url_open('/web/export/xlsx', data={
                'data': json.dumps(self.default_params),
                'token': 'dummy',
                'csrf_token': http.WebRequest.csrf_token(self),
            })

        # Main header
        self.assertEqual(self.worksheet[0, 0], "Partner name", "It should display the list header")
        self.assertEqual(self.worksheet[0, 1], "Comment", "It should display the list header")
        self.assertEqual(self.worksheet[0, 2], "Website", "It should display the list header")

        self.assertEqual(self.worksheet[1, 0], "fef (base.group_user)")
        self.assertEqual(self.worksheet[1, 1], "")
        self.assertEqual(self.worksheet[1, 2], "")

        self.assertEqual(self.worksheet[2, 0], "partner 1")
        self.assertEqual(self.worksheet[2, 1], "yop")
        self.assertEqual(self.worksheet[2, 2], "http://yop.com")

        self.assertEqual(self.worksheet[3, 0], "partner 2")
        self.assertEqual(self.worksheet[3, 1], "yop")
        self.assertEqual(self.worksheet[3, 2], "http://blop.com")

        self.assertEqual(self.worksheet[4, 0], "partner 3")
        self.assertEqual(self.worksheet[4, 1], "yop")
        self.assertEqual(self.worksheet[4, 2], "http://blop.com")

        self.assertEqual(self.worksheet[5, 0], "partner 4")
        self.assertEqual(self.worksheet[5, 1], "blop")
        self.assertEqual(self.worksheet[5, 2], "http://blop.com")
