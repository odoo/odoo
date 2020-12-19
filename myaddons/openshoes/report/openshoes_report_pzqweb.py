
from odoo import models, api



class report2(models.Model):
    # _name�����������������  report+����ģ����+openshoes_report_pzqweb.xmlģ��id��ɣ������棩
    _name = 'report.openshoes.report_library_book_template'

    def _get_data(self,ids):
        #sql���
        sql = "select * from openshoes_openshoes"
        # ���ֲ�ѯ����
        # cr.dictfetchall() �õ� [{'reg_no': 123},{'reg_no': 543},]
        # cr.dictfetchone() �õ� {'reg_no': 123}
        # cr.fetchall() �õ� '[(123),(543)]'
        # cr.fetchone() �õ� '(123)'
        # �ο�https://blog.csdn.net/qq_29654325/article/details/78019686
        self.env.cr.execute(sql)
        # DictObj��ʵ��dictתΪ�������ԣ��Ӷ����ݷ��ʿ���ͨ������ʽ����
        #��data2['name']ת����data2.name
        # �ο�https://blog.csdn.net/hk52222/article/details/103214581
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


