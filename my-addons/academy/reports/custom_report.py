from odoo import models, fields, api

class CustomReport(models.AbstractModel):
    _name = "report.academy.custom_report_template"

    def _get_lines_data(self, ids):
        ids = str(ids).replace('[', '(').replace(']', ')')
        sql='''
            select * from academy_teachers where id in %s %s
            ''' % (ids," And 1=1")
        self.env.cr.execute(sql)
        return self.env.cr.dictfetchall()

    @api.model
    def _get_report_values(self, docids, data=None):
        docis2 = docids
        data12 = data
        header_data = {'data': "TestReport"}
        data2 = self._get_lines_data(docids)
        dataList = []
        for x in data2:
           l=DictObj(x)
           dataList.append(l)
           
        docArgs ={
            "report_name": "test_report",
            "header_data": header_data,
            "lines_data": [{'data': "test2"}, {'data': "test3"}],
            "lines_data2":dataList,
            "docs":[{'id':1,'name':"custName"},{'id':11,'name':"custName11"}]
        }
        return docArgs

    def dict_to_object(self,dictObj):
        if not isinstance(dictObj, dict):
            return dictObj
        inst = DictObj()
        for k,v in dictObj.items():
            inst[k] = dict_to_object(v)
        return inst

class DictObj(object):
    def __init__(self,map):
        self.map = map
 
    def __setattr__(self, name, value):
        if name == 'map':
             object.__setattr__(self, name, value)
             return;
        print ('set attr called ',name,value)
        self.map[name] = value
 
    def __getattr__(self,name):
        v = self.map[name]
        if isinstance(v,(dict)):
            return DictObj(v)
        if isinstance(v, (list)):
            r = []
            for i in v:
                r.append(DictObj(i))
            return r
        else:
            return self.map[name];
 
    def __getitem__(self,name):
        return self.map[name]
