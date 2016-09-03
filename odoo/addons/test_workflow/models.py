# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, api
from odoo.workflow import trg_trigger

_logger = logging.getLogger(__name__)

class m(models.Model):
    """ A model for which we will define a workflow (see data.xml). """
    _name = 'test.workflow.model'

    @api.multi
    def _print(self, s):
        _logger.info('Running activity `%s` for record %s', s, self.ids)
        return True

    @api.multi
    def print_a(self):
        return self._print('a')

    @api.multi
    def print_b(self):
        return self._print('b')

    @api.multi
    def print_c(self):
        return self._print('c')

    @api.multi
    def condition(self):
        record = self.env['test.workflow.trigger'].browse(1)
        return bool(record.value)

    @api.model
    def trigger(self):
        return trg_trigger(self._uid, 'test.workflow.trigger', 1, self._cr)


class n(models.Model):
    """ A model used for the trigger feature. """
    _name = 'test.workflow.trigger'
    value = fields.Boolean(default=False)


class a(models.Model):
    _name = 'test.workflow.model.a'
    value = fields.Integer(default=0)


class b(models.Model):
    _name = 'test.workflow.model.b'
    _inherit = 'test.workflow.model.a'


class c(models.Model):
    _name = 'test.workflow.model.c'
    _inherit = 'test.workflow.model.a'


class d(models.Model):
    _name = 'test.workflow.model.d'
    _inherit = 'test.workflow.model.a'


class e(models.Model):
    _name = 'test.workflow.model.e'
    _inherit = 'test.workflow.model.a'


for name in 'bcdefghijkl':
    #
    # Do not use type() to create the class here, but use the class construct.
    # This is because the __module__ of the new class would be the one of the
    # metaclass that provides method __new__!
    #
    class NewModel(models.Model):
        _name = 'test.workflow.model.%s' % name
        _inherit = 'test.workflow.model.a'
