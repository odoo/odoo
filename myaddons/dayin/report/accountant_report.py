from odoo import models, fields, api


# _name= 'report.' +[���ݱ������]+ '.' +[template��id����]

class accountant_report(models.Model):
    _name = 'report.property_dayin.accountant_report'

    def _get_date(self):
        sql = "select * form property_dayin;"
        self._cr.execute(sql)
        return self._cr.fetchall()

    @api.model
    def get_report_values(self,docids,data=None):
        return self._get_data(docids)
