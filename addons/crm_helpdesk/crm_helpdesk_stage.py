# -*- coding: utf-8 -*-

from openerp import fields, models

class CrmHelpdeskStage(models.Model):
    
    _name = "crm.helpdesk.stage"
    _description = "helpdesk stages"
    
    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(default=lambda *args: 1, help="Used to order stages. Lower is better.")
    team_ids = fields.Many2many('crm.team', 'crm_team_helpdesk_stage_rel', 'stage_id', 'team_id', string='Teams',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams.")
    case_default = fields.Boolean(string='Common to All Teams',
                        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams.")
    fold = fields.Boolean(string='Folded in Kanban View',
                               help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.')
