# -*- coding: utf-8 -*-

from odoo import fields, models


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

    def stage_uniq(self):
        draft_list = []
        approve_list = []
        forclose_list = []
        amend_draft_list = []

        stage_obj_draft = self.env['stage.master'].search([('draft', '=', True)])
        for stage in stage_obj_draft:
            draft_list.append(stage.id)
            if len(set(draft_list)) > 1:
                return False

        stage_obj_approved = self.env['stage.master'].search([('approved', '=', True)])
        for stage in stage_obj_approved:
            approve_list.append(stage.id)
            if len(set(approve_list)) > 1:
                return False

        stage_obj_forclosed = self.env['stage.master'].search([('foreclosed', '=', True)])
        for stage in stage_obj_forclosed:
            forclose_list.append(stage.id)
            if len(set(forclose_list)) > 1:
                return False

        stage_obj_amend_draft = self.env['stage.master'].search([('amend_and_draft', '=', True)])
        for stage in stage_obj_amend_draft:
            amend_draft_list.append(stage.id)
            if len(set(amend_draft_list)) > 1:
                return False

        return True

    _constraints = [
        (stage_uniq, 'The draft, approved, foreclosed, amend_and_draft state must be unique!', ['draft', 'approved', 'foreclosed', 'amend_and_draft'])
    ]


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

