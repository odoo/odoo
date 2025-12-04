# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResourceTest(models.Model):
    _name = 'resource.test'
    _description = 'Test Resource Model'
    _inherit = ['resource.mixin']

    name = fields.Char()
    size = fields.Float()


class RelatedResourceTest1(models.Model):
    _name = "related.resource.test.1"
    _description = "First related node for resource test"

    resource_test_id = fields.Many2one("resource.test")
    size_related = fields.Float(related='resource_test_id.size')
    is_valid = fields.Boolean()
    surname = fields.Char()


class RelatedResourceTest2(models.Model):
    _name = "related.resource.test.2"
    _description = "Second related node for resource test"

    profile_picture = fields.Image()
    related_resource_test_1_id = fields.Many2one("related.resource.test.1")
    related_resource_test_id = fields.Many2one(
        string="Related Resource Test Id",
        related="related_resource_test_1_id.resource_test_id",
    )
    size_related_2 = fields.Float(
        related='related_resource_test_1_id.size_related',
    )
    is_valid_related = fields.Boolean(
        related='related_resource_test_1_id.is_valid',
    )
    resource_test_id = fields.Many2one("resource.test")
    name_related_orig = fields.Char(
        related='resource_test_id.name',
    )
