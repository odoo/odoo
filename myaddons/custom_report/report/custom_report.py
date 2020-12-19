# -*- coding: utf-8 -*-


from odoo import models, fields, api


# _name= 'report.' +[数据表的名称]+ '.' +[template的id名称]

class accountant_report(models.Model):
    _name = 'report.custom_report.custom_report_templates'

    @api.model
    def _get_report_values(self,docids,data=None):
        docs = self.env['custom.report'].browse(docids)
        print(docs)
        print(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'custom.report',
            'docs': docs,
            'proforma': True
        }