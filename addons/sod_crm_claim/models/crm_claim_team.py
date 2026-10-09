# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import _, fields, models


class CrmClaimTeam(models.Model):
    _name = "crm.claim.team"
    _description = "Crm Claim Team"
    #     _inherit = ['mail.alias.mixin', 'mail.thread']
    #     _order = 'sequence,name'

    def _get_default_warehouse(self):
        company_id = self.env.company.id
        wh_obj = self.env["stock.warehouse"]
        wh = wh_obj.search([("company_id", "=", company_id)], limit=1)
        if not wh:
            raise Warning(_("There is no warehouse for the current user's company."))
        return wh

    name = fields.Char("Crm Return Team", required=True, translate=True)
    description = fields.Text("About Team", translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env["res.company"]._company_default_get(
            "crm.claim.team"
        ),
    )
    sequence = fields.Integer(default=10)
    color = fields.Integer("Color Index", default=1)
    #     stage_ids = fields.Many2many(
    #         'helpdesk.stage', relation='team_stage_rel', string='Stages',
    # #         default=_default_stage_ids,
    # help="Stages the team will use.
    # This team's tickets will only be able to be in these stages.")
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        default=_get_default_warehouse,
        required=True,
    )
    member_ids = fields.Many2many("res.users", string="Team Members")
    claim_type = fields.Selection(
        [("customer", "Customer"), ("supplier", "Supplier")],
        string="Return Type",
        required=True,
        default="customer",
        help="customer = from customer to company ; supplier = from company to supplier",
    )


# class CrmClaimStage(models.Model):
#     _name = 'crm.claim.stage'
#     _description = 'Crm Claim Stage'
#     _order = 'sequence, id'
#
#     def _get_default_team_ids(self):
#         team_id = self.env.context.get('default_team_id')
#         if team_id:
#             return [(4, team_id, 0)]
#
#     name = fields.Char(required=True, translate=True)
#     sequence = fields.Integer('Sequence', default=10)
#     is_close = fields.Boolean(
#         'Closing Kanban Stage',
#         help='Tickets in this stage are considered as done. This is used notably when '
#              'computing SLAs and KPIs on tickets.')
#     fold = fields.Boolean(
#         'Folded', help='Folded in kanban view')
#     team_ids = fields.Many2many(
#         'crm.claim.team', relation='claim_team_stage_rel', string='Team',
#         default=_get_default_team_ids,
# help='Specific team that uses this stage.
# Other teams will not be able to see or use this stage.')
#
#
# @api.multi
# def unlink(self):
# stages = self
# default_team_id = self.env.context.get('default_team_id')
# if default_team_id:
# shared_stages = self.filtered(lambda x: len(x.team_ids) > 1 and \
# default_team_id in x.team_ids.ids)
# claims = self.env['crm.claim'].with_context(active_test=False).search(
# [('team_id', '=', default_team_id), ('stage_id', 'in', self.ids)])
# if shared_stages and not claims:
# shared_stages.write({'team_ids': [(3, default_team_id)]})
# stages = self.filtered(lambda x: x not in shared_stages)
# return super(CrmClaimStage, stages).unlink()
