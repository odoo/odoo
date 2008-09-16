# -*- encoding: utf-8 -*-
import time
import pooler
from report import report_sxw
import datetime

class analytic_account_budget_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(analytic_account_budget_report, self).__init__(cr, uid, name, context)
        self.localcontext.update( {
            'funct': self.funct,
            'funct_total': self.funct_total,
            'time': time,
        })
        self.context=context


    def funct(self,object,form,ids={}, done=None, level=1):

        if not ids:
            ids = self.ids
#        if not ids:
#            return []
        if not done:
            done={}

        global tot
        tot={
            'theo':0.00,
            'pln':0.00,
            'prac':0.00,
            'perc':0.00
        }
        result=[]
        accounts = self.pool.get('account.analytic.account').browse(self.cr, self.uid, [object.id], self.context.copy())

        for account_id in accounts:
            res={}
            budget_lines=[]
            b_line_ids=[]

            for line in account_id.crossovered_budget_line:
                b_line_ids.append(line.id)

            bd_lines_ids = ','.join([str(x) for x in b_line_ids])

            d_from=form['date_from']
            d_to=form['date_to']

            query="select id from crossovered_budget_lines where id in ("+ str(bd_lines_ids) + ")"# AND '"+ str(d_from) +"'<=date_from AND date_from<date_to AND date_to<= '"+ str(d_to) +"'"

            self.cr.execute(query)
            budget_line_ids=self.cr.fetchall()

            if not budget_line_ids:
                return []

            budget_lines=[x[0] for x in budget_line_ids]

            bd_ids = ','.join([str(x) for x in budget_lines])

            self.cr.execute('select distinct(crossovered_budget_id) from crossovered_budget_lines where id in (%s)'%(bd_lines_ids))
            budget_ids=self.cr.fetchall()

            for i in range(0,len(budget_ids)):

                budget_name=self.pool.get('crossovered.budget').browse(self.cr, self.uid,[budget_ids[i][0]])
                res={
                     'b_id':'-1',
                     'a_id':'-1',
                     'name':budget_name[0].name,
                     'status':1,
                     'theo':0.00,
                     'pln':0.00,
                     'prac':0.00,
                     'perc':0.00
                }
                result.append(res)

                line_ids = self.pool.get('crossovered.budget.lines').search(self.cr, self.uid, [('id', 'in', b_line_ids),('crossovered_budget_id','=',budget_ids[i][0])])
                line_id = self.pool.get('crossovered.budget.lines').browse(self.cr,self.uid,line_ids)
                tot_theo=tot_pln=tot_prac=tot_perc=0

                done_budget=[]
                for line in line_id:

                    if line.id in budget_lines:
                        theo=pract=0.00
                        theo=line._theo_amt(self.cr, self.uid, [line.id],"theoritical_amount",None,context={'wizard_date_from':d_from,'wizard_date_to':d_to})[line.id]
                        pract=line._pra_amt(self.cr, self.uid, [line.id],"practical_amount",None,context={'wizard_date_from':d_from,'wizard_date_to':d_to})[line.id]

                        if line.general_budget_id.id in done_budget:

                            for record in result:
                               if record['b_id']==line.general_budget_id.id  and record['a_id']==line.analytic_account_id.id:

                                    record['theo'] +=theo
                                    record['pln'] +=line.planned_amount
                                    record['prac'] +=pract
                                    record['perc'] +=line.percentage
                                    tot_theo +=theo
                                    tot_pln +=line.planned_amount
                                    tot_prac +=pract
                                    tot_perc +=line.percentage
                        else:

                            res1={
                                 'b_id':line.general_budget_id.id,
                                 'a_id':line.analytic_account_id.id,
                                 'name':line.general_budget_id.name,
                                 'status':2,
                                 'theo':theo,
                                 'pln':line.planned_amount,
                                 'prac':pract,
                                 'perc':line.percentage
                            }

                            tot_theo += theo
                            tot_pln +=line.planned_amount
                            tot_prac +=pract
                            tot_perc +=line.percentage
                            result.append(res1)
                            done_budget.append(line.general_budget_id.id)
                    else:
                       if line.general_budget_id.id in done_budget:
                            continue
                       else:
                            res1={
                                    'b_id':line.general_budget_id.id,
                                    'a_id':line.analytic_account_id.id,
                                     'name':line.general_budget_id.name,
                                     'status':2,
                                     'theo':0.00,
                                     'pln':0.00,
                                     'prac':0.00,
                                     'perc':0.00
                            }

                            result.append(res1)
                            done_budget.append(line.general_budget_id.id)

                if tot_theo==0.00:
                    tot_perc=0.00
                else:
                    tot_perc=float(tot_prac /tot_theo)*100

                result[-(len(done_budget) +1)]['theo']=tot_theo
                tot['theo'] +=tot_theo
                result[-(len(done_budget) +1)]['pln']=tot_pln
                tot['pln'] +=tot_pln
                result[-(len(done_budget) +1)]['prac']=tot_prac
                tot['prac'] +=tot_prac
                result[-(len(done_budget) +1)]['perc']=tot_perc

            if tot['theo']==0.00:
                tot['perc'] =0.00
            else:
                tot['perc']=float(tot['prac'] /tot['theo'])*100

        return result

    def funct_total(self,form):
        result=[]
        res={}
        res={
             'tot_theo':tot['theo'],
             'tot_pln':tot['pln'],
             'tot_prac':tot['prac'],
             'tot_perc':tot['perc']
        }
        result.append(res)

        return result

report_sxw.report_sxw('report.account.analytic.account.budget', 'account.analytic.account', 'addons/account_budget/report/analytic_account_budget_report.rml',parser=analytic_account_budget_report,header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

