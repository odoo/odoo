


from odoo import models, fields, api


# _name= 'report.' +[数据表的名称]+ '.' +[template的id名称]

class accountant_report(models.AbstractModel):
    _name = 'report.dayintest.accountant_report'

    # def _get_data(self,docids):
    #     sql = "select * form dayintest.dayintest"
    #     self.env.cr.execute(sql)
    #     return self.env.cr.fetchall()

    @api.model
    def _get_report_values(self,docids,data=None):
        return {
            "line_datas": [{'data':"data1"},{'data':"data2"}]
        }

