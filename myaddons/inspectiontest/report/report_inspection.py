
from odoo import models, api

class DictObj(object):
    def __init__(self, map):
        self.map = map

    def __setattr__(self, name, value):
        if name == 'map':
            object.__setattr__(self, name, value)
            return
        print('set attr called ', name, value)
        self.map[name] = value

    def __getattr__(self, name):
        v = self.map[name]
        if isinstance(v, (dict)):
            return DictObj(v)
        if isinstance(v, (list)):
            r = []
            for i in v:
                r.append(DictObj(i))
            return r
        else:
            return self.map[name]

    def __getitem__(self, name):
        return self.map[name]


class report2(models.Model):
    _name = 'report.pltest.report2_library_book_template'


    def _get_data(self,ids):
        sql = "select * from pltest_pltest"
        self.env.cr.execute(sql)
        return DictObj(self.env.cr.dictfetchall()[0])

    @api.model
    def _get_report_values(self,docids,data= None):
        docArgs = {
            'title2':"Test Title",
            'data2':self._get_data(docids)
                   }
        return docArgs


