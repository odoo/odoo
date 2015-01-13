from openerp import fields, models, SUPERUSER_ID
from psycopg2 import IntegrityError


class pageview(models.Model):
    _name = "website.crm.pageview"

    view_date = fields.Datetime(string='Viewing Date')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    partner_id = fields.Many2one('res.partner', string='Partner')
    url = fields.Char(string='Url')

    def create_pageview(self, cr, uid, vals, context=None, test=False):
        # returns True if the operation in the db was successful, False otherwise
        lead_id = vals.get('lead_id', None)
        partner_id = vals.get('partner_id', None)
        url = vals.get('url', None)
        view_date = fields.Datetime.now()

        # registry = modules.registry.RegistryManager.get(request.session.db)
        # with registry.cursor() as pv_cr:
        with self.pool.cursor() as pv_cr:
            if test:
                pv_cr = cr
            pv_cr.execute('''
                UPDATE website_crm_pageview SET view_date=%s WHERE lead_id=%s AND url=%s RETURNING id;
                ''', (view_date, lead_id, url))
            fetch = pv_cr.fetchone()
            if fetch:
                return True
            else:
                # update failed
                try:
                    pv_cr.execute('''
                        INSERT INTO website_crm_pageview (lead_id, partner_id, url, view_date)
                        SELECT %s,%s,%s,%s
                        RETURNING id;
                        ''', (lead_id, partner_id, url, view_date))
                    fetch = pv_cr.fetchone()
                    if fetch:
                        # a new pageview has been created, a message is posted
                        body = '<a href="' + url + '" target="_blank"><b>' + url + '</b></a>'
                        self.pool['crm.lead'].message_post(cr, SUPERUSER_ID, [lead_id], body=body, subject="Page visited", context=context)
                        return True
                except IntegrityError:
                    return False
