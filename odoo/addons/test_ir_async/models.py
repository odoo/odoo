# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import UserError


class TestIrAsyncModel(models.Model):
    _name = 'test_ir_async'
    _description = 'Dummy model for experimentation'

    call_count = 0

    name = fields.Char()

    @api.model
    def echo_model(self, a, b, *args, d, e=5, **kwargs):
        """ Support for model methods and complexe signatures """
        TestIrAsyncModel.call_count += 1
        return (a, b, *args, d, e, kwargs)

    def swap_name(self):
        """ Support for recordset operations """
        TestIrAsyncModel.call_count += 1
        for dummy in self:
            dummy.name = self.name.swapcase()

    def async_echo(self, count):
        """ Recursive asynchronous tasks """
        TestIrAsyncModel.call_count += 1
        if count > 0:
            return self.env['ir.async'].call(self.async_echo, count - 1).id
        return self.echo_model(1, 2, 3, d=4)

    def faulty_layer_8(self):
        """ User Error should WARNING """
        TestIrAsyncModel.call_count += 1
        raise UserError("Bad bad bad user")

    def annoying_cosmic_ray(self):
        """ Other exceptions should ERROR """
        TestIrAsyncModel.call_count += 1
        raise ValueError("A cosmic ray fucked up the system")

    def async_cosmic_ray(self, count):
        """ Complete traceback is kept """
        TestIrAsyncModel.call_count += 1
        if count > 0:
            return self.env['ir.async'].call(self.async_cosmic_ray, count - 1).id
        return self.annoying_cosmic_ray()

    def commit_raise(self):
        TestIrAsyncModel.call_count += 1
        self.ensure_one()
        self.name += 'erronous'
        raise ValueError()
