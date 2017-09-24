# -*- coding: utf-8 -*-
from odoo import models, fields, api
import random
import logging

_logger = logging.getLogger(__name__)


def sql_count(target=None, log=False):
    def _count_decorator(method):
        def wrap(self):
            if log:
                oldlog = self.env.cr.sql_log
                self.env.cr.sql_log = True
            count = self.env.cr.sql_log_count
            result = method(self)
            if not (target is None):
                _logger.info('Count %s: %d', method.__name__, self.env.cr.sql_log_count - count)
            elif (self.env.cr.sql_log_count - count)>target:
                _logger.info('Count %s: %d (target: %d)', method.__name__, self.env.cr.sql_log_count - count, target)
            if log:
                self.env.cr.sql_log = oldlog
            return result
        return wrap
    return _count_decorator

class speed_test(models.Model):
    _name = 'speed_test.speed_test'
    _inherit = 'mail.thread'

    name = fields.Char()
    value = fields.Integer()
    track = fields.Char(default='test', track_visibility="onchange")
    value2 = fields.Float(compute="_value_pc", store=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value2 = float(record.value) / 100

    @sql_count(target=3)
    def _check_country(self):
        for speed in self:
            speed.partner_id.country_id.name

    @sql_count(target=0, log=True)
    def _check_value2(self):
        for speed in self:
            speed.value2

    @sql_count(target=3)
    def _check_write_multi(self):
        self.write({'value': 40})

    @sql_count(target=10)
    def _check_write(self):
        for speed in self:
            speed.value = random.randint(10,40)

    @sql_count(target=4)
    def check_create(self):
        self.with_context(tracking_disable=True).create({'name': 'kjkj'})

    @sql_count(target=4, log=True)
    def check_create_track(self):
        self.create({'name': 'kjkjmlkm'})

    @sql_count(target=4)
    def check_track(self):
        obj = self[0]
        obj.track = str(random.randint(0,1000))

    def check(self):
        # Without Cache
        self._check_country()

        # With Cache
        self._check_country()

        self._check_value2()
        self._check_write_multi()
        self._check_write()

        self.check_create()
        self.check_create_track()
        self.check_track()

