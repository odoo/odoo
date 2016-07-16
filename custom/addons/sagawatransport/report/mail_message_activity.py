# -*- coding: utf-8 -*-

import time
from openerp import api, models, _
from collections import defaultdict

class ReportCrmActivityMail (models.AbstractModel):

    _name = 'report.sagawatransport.report_crm_activity_mail'

    def _get_lines(self, form):
        cr = self.env.cr
        cr.execute('SELECT crm_activity.subtype_id FROM crm_activity')
        subtypes = cr.dictfetchall()
        subtypes_ids = [subtype['subtype_id'] for subtype in subtypes]
        if not subtypes_ids:
            return []
        cr.execute('SELECT crm_lead.name as name, mail_message.create_date as date, mail_message.body as body FROM mail_message JOIN crm_lead ON crm_lead.id = mail_message.res_id WHERE mail_message.model = %s and mail_message.create_date >= %s and mail_message.create_date <= %s and mail_message.subtype_id in %s  and mail_message.create_uid = %s', ('crm.lead', form['date1'], form['date2'],tuple(subtypes_ids), self.env.uid))
        messages = cr.dictfetchall()
        messages_by_lead_name = defaultdict(list)
        for message in messages:
            messages_by_lead_name[message['name']].append({'date': message['date'], 'body': message['body']})
        return messages_by_lead_name



    @api.multi
    def render_html(self, data):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        get_lines = self._get_lines(data['form'])
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'get_lines': get_lines,
            'time': time,

        }
        return self.env['report'].render('sagawatransport.report_crm_activity_mail', docargs)
