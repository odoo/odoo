#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# models
# ---------------------------------------------------------------------
# Copyright (c) 2017 Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2017-07-03

'''Test that unlinks properly propagate.

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


from openerp import models, fields, api


class Child(models.Model):
    _name = 'test_unlink.child'

    name = fields.Char(string='Child name')
    value = fields.Integer(string='Child value')
    owner_id = fields.Many2one('test_unlink.owner', ondelete='cascade')
    parent_id = fields.Many2one('test_unlink.parent')

    _sql_constraints = [
        ('owner_unique', 'unique (owner_id)', 'One2one actually')
    ]


class Owner(models.Model):
    _name = 'test_unlink.owner'
    item_id = fields.One2many('test_unlink.child', 'owner_id')


class Parent(models.Model):
    _name = 'test_unlink.parent'

    @api.depends('children_ids')
    def _compute_total(self):
        for record in self:
            record.total = sum(child.value for child in record.children_ids)

    name = fields.Char(string='Parent name')
    children_ids = fields.One2many('test_unlink.child', 'parent_id')
    total = fields.Integer(string='Total sum of children',
                           compute='_compute_total',
                           store=True)
