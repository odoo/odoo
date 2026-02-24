# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TransactionStatus(models.Model):
    _name = 'transaction.status'
    _description = 'Transaction Status'
    name = fields.Char('Name', required=True)


class StateMaster(models.Model):
    _name = 'stage.master'
    _description = 'State Master'

    name = fields.Char('Stage Name', required=True, translate=True)
    draft = fields.Boolean('Drafts')
    approved = fields.Boolean('Approved')
    foreclosed = fields.Boolean('Foreclosed')
    amend_and_draft = fields.Boolean('Amend And Draft')
    model = fields.Many2one('ir.model')
    groups = fields.Many2one('res.groups')

    @api.constrains('draft', 'approved', 'foreclosed', 'amend_and_draft')
    def _check_stage_uniq(self):
        for record in self:
            if record.draft and self.search_count([('draft', '=', True)]) > 1:
                raise ValidationError('The draft state must be unique!')
            if record.approved and self.search_count([('approved', '=', True)]) > 1:
                raise ValidationError('The approved state must be unique!')
            if record.foreclosed and self.search_count([('foreclosed', '=', True)]) > 1:
                raise ValidationError('The foreclosed state must be unique!')
            if record.amend_and_draft and self.search_count([('amend_and_draft', '=', True)]) > 1:
                raise ValidationError('The amend_and_draft state must be unique!')


class StateTransaction(models.Model):
    _name = "stage.transaction"
    _description = 'State Transaction'

    from_stage = fields.Many2one('stage.master', 'From Stage', required=True)
    to_stage = fields.Many2one('stage.master', 'To Stage', required=True)
    model = fields.Many2one('ir.model')
    groups = fields.Many2one('res.groups')


class TransactionStage(models.Model):
    _name = 'transaction.stage'
    _description = 'Transaction Stage'

    name = fields.Char('Stage Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1)
    draft = fields.Boolean('Drafts')
    approved = fields.Boolean('Approved')
    model = fields.Many2one('ir.model')

