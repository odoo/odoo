
from odoo import models, api



class report2(models.Model):
    # _name内容由三个部分组成  report+关联模块名+openshoes_report_pzqweb.xml模板id组成（在下面）
    _name = 'report.openshoes.report_library_book_template'

    def _get_data(self,ids):
        #sql语句
        sql = "select * from openshoes_openshoes"
        # 四种查询方法
        # cr.dictfetchall() 得到 [{'reg_no': 123},{'reg_no': 543},]
        # cr.dictfetchone() 得到 {'reg_no': 123}
        # cr.fetchall() 得到 '[(123),(543)]'
        # cr.fetchone() 得到 '(123)'
        # 参考https://blog.csdn.net/qq_29654325/article/details/78019686
        self.env.cr.execute(sql)
        # DictObj类实现dict转为对象属性，从而数据访问可以通过对象方式访问
        #例data2['name']转换成data2.name
        # 参考https://blog.csdn.net/hk52222/article/details/103214581
        return DictObj(self.env.cr.dictfetchall()[0])

    @api.model
    def _get_report_values(self,docids,data= None):
        docArgs = {
            'title2':"Test Title",
            'data2':self._get_data(docids)
                   }
        return docArgs

class DictObj(object):
    def __init__(self, map):
        self.map = map

    def __setattr__(self, name, value):
        if name == 'map':
            object.__setattr__(self, name, value)
            return;
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
            return self.map[name];

    def __getitem__(self, name):
        return self.map[name]


