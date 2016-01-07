# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class crm_stage(osv.Model):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    _columns = {
        'name': fields.char('Stage Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'probability': fields.float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success"),
        'on_change': fields.boolean('Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity."),
        'requirements': fields.text('Requirements', help="Enter here the internal requirements for this stage (ex: Offer sent to customer). It will appear as a tooltip over the stage's name."),
        'team_id': fields.many2one('crm.team', 'Team',
                                   ondelete='set null',
                                   help='Specific team that uses this stage. Other teams will not ne able to see or use this stage.'),
        'legend_priority': fields.text(
            'Priority Management Explanation', translate=True,
            help='Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.'),
        'fold': fields.boolean('Folded in Pipeline',
                               help='This stage is folded in the kanban view when '
                               'there are no records in that stage to display.'),
    }

    _defaults = {
        'sequence': 1,
        'probability': 10.0,
        'fold': False,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context and context.get('default_team_id') and not context.get('crm_team_mono', False):
            context = dict(context)
            context.pop('default_team_id')
        return super(crm_stage, self).default_get(cr, uid, fields, context=context)
