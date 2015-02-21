# -*- coding: utf-8 -*-
from openerp import fields, models, api
from openerp.tools.safe_eval import safe_eval
from openerp.osv.expression import expression
import datetime
import logging


_logger = logging.getLogger(__name__)
evaluation_context = {
    'datetime': datetime,
    'context_today': datetime.datetime.now,
}


class website_crm_score(models.Model):
    _name = 'website.crm.score'

    @api.one
    def _count_leads(self):
        if self.id:
            self._cr.execute("""
                 SELECT COUNT(1)
                 FROM crm_lead_score_rel
                 WHERE score_id = %s
                 """, (self.id,))
            self.leads_count = self._cr.fetchone()[0]
        else:
            self.leads_count = 0

    @api.one
    @api.constrains('domain')
    def _assert_valid_domain(self):
        try:
            domain = safe_eval(self.domain or '[]', evaluation_context)
            self.env['crm.lead'].search(domain)
        except Exception as e:
            _logger.warning('Exception: %s' % (e,))
            raise Warning('The domain is incorrectly formatted')

    name = fields.Char('Name', required=True)
    value = fields.Float('Value', required=True)
    domain = fields.Char('Domain', required=True)
    running = fields.Boolean('Active', default=True)
    leads_count = fields.Integer(compute='_count_leads')

    # the default [] is needed for the function to be usable by the cron
    @api.model
    def assign_scores_to_leads(self, ids=[]):
        domain = [('running', '=', True)]
        if ids:
            domain.append(('id', 'in', ids))
        scores = self.search_read(domain=domain, fields=['domain'])
        for score in scores:
            domain = safe_eval(score['domain'], evaluation_context)

            # Don't replace the domain with a 'not in' like below... that doesn't make the same thing !!!
            # domain.extend(['|', ('stage_id.on_change', '=', False), ('stage_id.probability', 'not in', [0,100])])
            domain.extend(['|', ('stage_id.on_change', '=', False), '&', ('stage_id.probability', '!=', 0), ('stage_id.probability', '!=', 100)])

            e = expression(self._cr, self._uid, domain, self.pool['crm.lead'], self._context)
            where_clause, where_params = e.to_sql()

            where_clause += """ AND (id NOT IN (SELECT lead_id FROM crm_lead_score_rel WHERE score_id = %s)) """
            where_params.append(score['id'])

            self._cr.execute("""INSERT INTO crm_lead_score_rel
                                    SELECT crm_lead.id as lead_id, %s as score_id
                                    FROM crm_lead
                                    WHERE %s RETURNING lead_id""" % (score['id'], where_clause), where_params)

            # Force recompute of fields that depends on score_ids
            lead_ids = [resp[0] for resp in self._cr.fetchall()]
            leads = self.env["crm.lead"].browse(lead_ids)
            leads.modified(['score_ids'])
            leads.recompute()
