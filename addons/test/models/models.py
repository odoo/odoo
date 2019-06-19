# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time

class test_mix(models.Model):
    """
        test object
    """
    _name = 'test.main'
    _log_access = False
    _description = "Test"

    name = fields.Char()
    booltest = fields.Boolean('Is False')
    int1 = fields.Integer('Int Def 1', default=lambda x: 1)
    child_ids = fields.One2many('test', 'test_main_id')


class test(models.Model):
    """
        test object
    """
    _name = 'test'
    _log_access = False
    _description = "Test"

    _inherits = {'test.main': 'test_main_id'}

    test_main_id = fields.Many2one('test.main', required=True, ondelete='cascade')
    line_ids = fields.One2many('test.line', 'test_id')
    intx2 = fields.Integer('Int x2', compute="_get_intx2", inverse='_set_intx2', store=True)
    line_sum = fields.Integer('Sum Currency', compute='_line_sum', store=True)

    @api.depends('line_ids.intx2')
    def _line_sum(self):
        for record in self:
            total = 0
            for line in record.line_ids:
                total += line.intx2
            record.line_sum = total

    @api.depends('int1')
    def _get_intx2(self):
        for record in self:
            record.intx2 = record.int1 * 2

    def _set_intx2(self):
        for record in self:
            record.int1 = record.intx2 // 2

    def testme(self):
        recs = self.env['res.partner'].search([])
        t = time.time()
        recs._read(['name', 'website','ref','country_id'])
        return time.time()-t

    def testme2(self):
        t = time.time()
        main_id = self.create({
            'name': 'bla',
            'line_ids': [
                (0,0, {'name': 'abc'}),
                (0,0, {'name': 'def'}),
            ]
        })
        if hasattr(self, 'flush'):
            self.flush()
        return time.time()-t

    def testme3(self):
        t = time.time()
        print('* Create with two lines')
        main = self.create({
            'name': 'bla',
            'line_ids': [
                (0,0, {'name': 'abc'}),
                (0,0, {'name': 'def'}),
            ]
        })
        print('* main.int1 = 5')
        main.int1 = 5
        print('* main.intx2 = 8')
        main.intx2 = 8
        print('* create_line')
        self.env['test.line'].create(
            {'name': 'ghi', 'test_id': main.id}
        )
        print('* search intx2 line')
        self.env['test.line'].search([('intx2', '=', 3)])
        print('* end')
        if hasattr(self, 'flush'):
            self.flush()
        return time.time()-t

    def testme4(self):
        t = time.time()
        main_id = self.env['test.main'].create({
            'name': 'bla',
        })
        if hasattr(self, 'flush'):
            self.flush()
        return time.time()-t


    def test(self):
        main = self.create({
            'name': 'main',
        })
        second = self.create({
            'name': 'second',
        })

        self.recompute()
        crash_here_to_rollback          # noqa


class test_line(models.Model):
    """
        test line
    """
    _name = 'test.line'
    _description = "Test Line"

    name = fields.Char(compute='_get_name', store=True)
    name2 = fields.Char('Related Name', related='test_id.name', store=True)

    test_id = fields.Many2one('test')
    intx2   = fields.Integer(compute='_get_intx2', store=True)

    @api.depends('test_id.test_main_id.name')
    def _get_name(self):
        for record in self:
            record.name = record.test_id.test_main_id.name

    @api.depends('test_id.intx2')
    def _get_intx2(self):
        for record in self:
            record.intx2 = record.test_id.intx2


