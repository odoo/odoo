import base64
import io
from collections import OrderedDict
from datetime import date, datetime
from unittest.mock import patch
from contextlib import contextmanager

import psycopg2
from PIL import Image

from odoo import Command, fields, models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged, users
from odoo.tools import BinaryBytes, float_repr, mute_logger
from odoo.tools.image import binary_to_image, image_data_uri

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.base.tests.files import SVG_RAW, ZIP_RAW
from odoo.addons.test_orm.tests.test_domain_expression import TransactionExpressionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestFields(TransactionCaseWithUserDemo, TransactionExpressionCase):
    def setUp(self):
        # for tests methods that create custom models/fields
        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_all_caches)
        super().setUp()
        self.env.ref('test_orm.discussion_0').write({'participants': [Command.link(self.user_demo.id)]})
        # YTI FIX ME: The cache shouldn't be inconsistent (rco is gonna fix it)
        # self.env.ref('test_orm.discussion_0').participants -> 1 user
        # self.env.ref('test_orm.discussion_0').invalidate()
        # self.env.ref('test_orm.discussion_0').with_context(active_test=False).participants -> 2 users
        self.env.ref('test_orm.message_0_1').write({'author': self.user_demo.id})

    def test_53_boolean_query(self):
        Model = self.env['test_orm.model_active_field']

        with self.assertQueries(["""
            SELECT "test_orm_model_active_field"."id"
            FROM "test_orm_model_active_field"
            WHERE "test_orm_model_active_field"."active" IS TRUE
            ORDER BY "test_orm_model_active_field"."id"
        """, """
            SELECT "test_orm_model_active_field"."id"
            FROM "test_orm_model_active_field"
            WHERE "test_orm_model_active_field"."active" IS NOT TRUE
            ORDER BY "test_orm_model_active_field"."id"
        """]):
            Model.search([('active', '=', True)])
            Model.search([('active', '=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_model_active_field"."id"
            FROM "test_orm_model_active_field"
            ORDER BY "test_orm_model_active_field"."id"
        """]):
            Model.search([('active', 'in', [True, False])])
        with self.assertQueries([]):
            Model.search([('active', 'not in', [True, False])])
