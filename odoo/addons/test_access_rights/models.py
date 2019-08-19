# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class SomeObj(models.Model):
    _name = 'test_access_right.some_obj'
    _description = 'Object For Test Access Right'

    val = fields.Integer()
    categ_id = fields.Many2one('test_access_right.obj_categ')


class Container(models.Model):
    _name = 'test_access_right.container'
    _description = 'Test Access Right Container'

    some_ids = fields.Many2many('test_access_right.some_obj', 'test_access_right_rel', 'container_id', 'some_id')


class ObjCateg(models.Model):
    _name = 'test_access_right.obj_categ'
    _description = "Context dependent searchable model"

    name = fields.Char(required=True)

    def search(self, args, **kwargs):
        if self.env.context.get('only_media'):
            args += [('name', '=', 'Media')]
        return super(ObjCateg, self).search(args, **kwargs)
