# -*- encoding: utf-8 -*-
#Copyright (c) Vincent Cardon <vincent.cardon@tranquil-it-systems.fr>
# Denis Cardon <denis.cardon@tranquilitsystems.com> and Emmanuel RICHARD.
#Ingenieur fondateur
#Tranquil IT Systems


import wizard
import time
import datetime
import pooler
import sys
from mx.DateTime import *
from pdf_ext import *
import tools

finished_form='''<?xml version="1.0"?>
<form string="Mail send ">
    <label string="Operation Completed Successfully ! " colspan="4"/>
    </form>'''


_aged_trial_form = """<?xml version="1.0"?>
<form string="Aged Trial Balance">
    <field name="company_id"/>
    <newline/>
    <field name="fiscalyear"/>
    <label align="0.7" colspan="6" string="(If you do not select Fiscal year it will take all open fiscal year)"/>
    <newline/>
    <field name="target_move"/>
</form>"""

_aged_trial_fields = {
    'company_id': {'string': 'Company', 'type': 'many2one', 'relation': 'res.company', 'required': True},
    'fiscalyear': {'string': 'Fiscal year', 'type': 'many2one', 'relation': 'account.fiscalyear',
    'help': 'Keep empty for all open fiscal year'},
    'target_move':{'string': 'Target Moves', 'type': 'selection', 'selection': [('all','All Entries'),('posted_only','All Posted Entries')], 'required': True, 'default': lambda *a:"all"}
}
start_date_year_n="2008-01-01"
end_date_year_n='2008-12-31'
start_date_year_n_minus_one='2007-01-01'
end_date_year_n_minus_one='2007-12-31'
company_name="Tiny Sprl"
debug=True
mytable={}
value=[]

def rightpadding(cr,uid,mystring,padder):
    return mystring + padder*(6-len(mystring))

def sumAll(cr,uid,account_from_in,account_to_in,year):
    global start_date_year_n, end_date_year_n, start_date_year_n_minus_one, end_date_year_n_minus_one
    if year == 'n':
        return sumAll_start_stop(cr,uid,account_from_in,account_to_in,start_date_year_n,end_date_year_n)
    else:
        return sumAll_start_stop(cr,uid,account_from_in,account_to_in,start_date_year_n_minus_one,end_date_year_n_minus_one)

def sumDebtor(cr,uid,account_from_in,account_to_in,year):
    global start_date_year_n, end_date_year_n, start_date_year_n_minus_one, end_date_year_n_minus_one
    if year == 'n':
        return sumDebtor_start_stop(cr,uid,account_from_in,account_to_in,start_date_year_n,end_date_year_n)
    else:
        return sumDebtor_start_stop(cr,uid,account_from_in,account_to_in,start_date_year_n_minus_one,end_date_year_n_minus_one)

def sumCreditor(cr,uid,account_from_in,account_to_in,year):
    global start_date_year_n, end_date_year_n, start_date_year_n_minus_one, end_date_year_n_minus_one
    if year == 'n':
        return sumCreditor_start_stop(cr,uid,account_from_in,account_to_in,start_date_year_n,end_date_year_n)
    else:
        return sumCreditor_start_stop(cr,uid,account_from_in,account_to_in,start_date_year_n_minus_one,end_date_year_n_minus_one)

def sumAll_start_stop(cr,uid,account_from_in,account_to_in,date_start,date_stop):
    global value
    account_from = rightpadding(cr,uid,account_from_in,"0")
    account_to = rightpadding(cr,uid,account_to_in,"9")
    query = """
        select sum(debit),sum(credit)
        from account_account,account_move_line,account_period,account_move
        where
            account_account.id = account_move_line.account_id
            and account_period.id = account_move_line.period_id
            AND account_move_line.move_id=account_move.id
            AND account_move.state IN """+str(value)+"""
            and account_account.code >= '""" + account_from + """'
            and account_account.code <= '""" + account_to + """'
            and account_period.date_start >='""" + date_start + """'
            and account_period.date_stop <= '""" + date_stop + """'
    """
    cr.execute(query)
    row =cr.fetchone()
    try:
        return row[0] - row[1]
    except TypeError:
        return 0

    #This function calculates the sum of the Debtor accounts that are beetween 2 account numbers : $accNo1 and $accNo2
def sumDebtor_start_stop(cr,uid,account_from_in,account_to_in,date_start,date_stop):
    global value
    account_from = rightpadding(cr,uid,account_from_in,"0")
    account_to = rightpadding(cr,uid,account_to_in,"9")

    sumDebtor=0;

    queryAccount = """SELECT distinct account_account.code FROM account_account WHERE code >= '""" + account_from + """' and code <= '""" + account_to  +  """'"""
    resultAccount =cr.execute(queryAccount)
    rows =cr.fetchall()
    for row in rows:
        query="""
        select sum(debit),sum(credit)
                from account_account,account_move_line,account_period,account_move
                where
                        account_account.id = account_move_line.account_id
                        and account_period.id = account_move_line.period_id
                        AND account_move_line.move_id=account_move.id
                        AND account_move.state IN """+str(value)+"""
                        and account_account.code = '""" + row[0] + """'
                        and account_period.date_start >='""" + date_start + """'
                        and account_period.date_stop <= '""" + date_stop + """'
        """
        cr.execute(query)
        row2 =cr.fetchone()
        try:
            if row2[1] - row2[0] < 0:
                sumDebtor = sumDebtor - ( row2[1] - row2[0])
        except TypeError:
            sumDebtor = sumDebtor

    return sumDebtor

def sumCreditor_start_stop(cr,uid,account_from_in,account_to_in,date_start,date_stop):
    global value
    account_from = rightpadding(cr,uid,account_from_in,"0")
    account_to = rightpadding(cr,uid,account_to_in,"9")

    sumCreditor=0;

    queryAccount = """SELECT distinct account_account.code FROM account_account WHERE code >= '""" + account_from + """' and code <= '""" + account_to  +  """'"""
    resultAccount =cr.execute(queryAccount)
    rows =cr.fetchall()

    query = None
    for row in rows:
            query="""
    select sum(debit),sum(credit)
            from account_account,account_move_line,account_period,account_move
            where
                    account_account.id = account_move_line.account_id
                    and account_period.id = account_move_line.period_id
                    AND account_move_line.move_id=account_move.id
                    AND account_move.state IN """+str(value)+"""
                    and account_account.code = '""" + row[0] + """'
                    and account_period.date_start >='""" + date_start + """'
                    and account_period.date_stop <= '""" + date_stop + """'
    """
    if query:
        result=cr.execute(query)
        row2 =cr.fetchone()
    else:
        row2 = (0.0,0.0)
    try:
        if row2[1] - row2[0] > 0:
            sumCreditor = sumCreditor + (row2[1] - row2[0])
    except TypeError:
        sumCreditor = sumCreditor

    return sumCreditor

def sumOfVar(cr,uid,varTemplate,from_range,to_range):
    global mytable
    result = 0
    myvar = varTemplate
    for n in range(from_range,to_range+1):
        varname = myvar.replace('xx',str(n))
        try:
            result = result + float(mytable[varname])
        except KeyError:
            result = result
    return result

def diffOfVar(cr,uid,varTemplate,from_range,to_range):
    global mytable
    myvar = varTemplate
    varname1 = myvar.replace('xx',str(from_range))
    varname2 = myvar.replace('xx',str(to_range))
    return  float(mytable[varname1]) - float(mytable[varname2])

def negative(myvar):
    return -1 * myvar

def _calc_dates(cr, uid, data, context):
    res = {}
    return res

def _get_move_states(val):
    if val == 'all':
        return ('draft','posted')
    else:
        return ('posted','')

def _test(self,cr,uid,data,context):
    global mytable, start_date_year_n, end_date_year_n, start_date_year_n_minus_one, end_date_year_n_minus_one,company_name,value
    mytable={}
    fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')
    fyear=fiscalyear_obj.browse(cr,uid,data['form']['fiscalyear'])
    comp_obj=pooler.get_pool(cr.dbname).get('res.company').browse(cr, uid, data['form']['company_id'])
    company_name=comp_obj.name
    start_date_year_n=fyear.date_start
    end_date_year_n=fyear.date_stop
    newdate=datetime.date.fromtimestamp(time.mktime(time.strptime(fyear.date_start, '%Y-%m-%d')))
    start_date_year_n_minus_one=newdate.replace(newdate.year-1).strftime('%Y-%m-%d')
    newdate=datetime.date.fromtimestamp(time.mktime(time.strptime(fyear.date_stop, '%Y-%m-%d')))
    end_date_year_n_minus_one=newdate.replace(newdate.year-1).strftime('%Y-%m-%d')
    value = _get_move_states(data['form']['target_move'])

    val_dict={ 'RN_A2_1_1':"abs(sumAll(cr,uid,'109','109','n') )",'RN_ZCL_1':"abs(sumAll(cr,uid,'109','109','n'))",
        'RN_A2_1_2':"abs(sumAll(cr,uid,'109','109','n-1'))",'RN_A2_2_1':"abs(sumAll(cr,uid,'200','202','n'))",
        'RN_A2_2_2':"abs(sumAll(cr,uid,'2800','2802','n'))",'RN_ZCL_2':"abs( diffOfVar(cr,uid,'RN_A2_2_xx',1,2))",
        'RN_A2_2_3':"abs(sumAll(cr,uid,'200','202','n-1'))-abs(sumAll(cr,uid,'2800','2802','n-1'))",
        'RN_A2_3_1':"abs(sumAll(cr,uid,'203','204','n'))",'RN_A2_3_2':"abs(sumAll(cr,uid,'2803','2804','n'))",
        'RN_ZCL_3':"abs( diffOfVar(cr,uid,'RN_A2_3_xx',1,2))",'RN_A2_3_3':"abs(sumAll(cr,uid,'203','204','n-1'))-abs(sumAll(cr,uid,'2803','2804','n-1'))",
        'RN_A2_4_1':"abs(sumAll(cr,uid,'205','205','n'))",'RN_A2_4_2':"abs(sumAll(cr,uid,'2805','2806','n'))+abs(sumAll(cr,uid,'2900','2905','n'))",
        'RN_ZCL_4':"abs( diffOfVar(cr,uid,'RN_A2_4_xx',1,2))",'RN_A2_4_3':"abs(sumAll(cr,uid,'205','205','n-1'))-abs(sumAll(cr,uid,'2805','2806','n-1'))-abs(sumAll(cr,uid,'2900','2905','n-1'))",
        'RN_A2_5_1':"abs(sumAll(cr,uid,'206','207','n') )",'RN_A2_5_2':"abs(sumAll(cr,uid,'2807','2807','n'))+abs(sumAll(cr,uid,'2906','2907','n') )",
        'RN_ZCL_5':"abs( diffOfVar(cr,uid,'RN_A2_5_xx',1,2) )",'RN_A2_5_3':"abs(sumAll(cr,uid,'206','207','n-1'))-abs(sumAll(cr,uid,'2807','2807','n-1'))-abs(sumAll(cr,uid,'2906','2907','n-1') )",
        'RN_A2_6_1':"abs(sumAll(cr,uid,'208','209','n'))+abs(sumAll(cr,uid,'232','236','n') )",'RN_A2_6_2':"abs(sumAll(cr,uid,'2808','2809','n'))+abs(sumAll(cr,uid,'2908','2909','n') )",
        'RN_ZCL_6' :"abs( diffOfVar(cr,uid,'RN_A2_6_xx',1,2)  )",'RN_A2_6_3':"abs(sumAll(cr,uid,'208','209','n-1'))+abs(sumAll(cr,uid,'232','236','n-1'))-abs(sumAll(cr,uid,'2808','2809','n-1'))-abs(sumAll(cr,uid,'2908','2909','n-1') )",
        'RN_A2_7_1':"abs(sumAll(cr,uid,'237','237','n') )",'RN_A2_7_2':"abs(sumAll(cr,uid,'2830','2837','n'))+abs(sumAll(cr,uid,'2937','2937','n') )",
        'RN_ZCL_7':"abs( diffOfVar(cr,uid,'RN_A2_7_xx',1,2) )",'RN_A2_7_3':"abs(sumAll(cr,uid,'237','237','n-1'))-abs(sumAll(cr,uid,'2830','2837','n-1'))-abs(sumAll(cr,uid,'2937','2937','n-1') )",
        'RN_A2_8_1':"abs(sumAll(cr,uid,'210','212','n') )",'RN_A2_8_2':"abs(sumAll(cr,uid,'2810','2812','n'))+abs(sumAll(cr,uid,'2910','2914','n') )",
        'RN_ZCL_8':"abs( diffOfVar(cr,uid,'RN_A2_8_xx',1,2) )",'RN_A2_8_3':"abs(sumAll(cr,uid,'210','212','n-1'))-abs(sumAll(cr,uid,'2810','2812','n-1'))-abs(sumAll(cr,uid,'2910','2914','n-1') )",
        'RN_A2_9_1':"abs(sumAll(cr,uid,'213','214','n') )",'RN_A2_9_2':"abs(sumAll(cr,uid,'2813','2814','n'))+abs(sumAll(cr,uid,'2913','2914','n') )",
        'RN_ZCL_9':"abs( diffOfVar(cr,uid,'RN_A2_9_xx',1,2) )",'RN_A2_9_3':"abs(sumAll(cr,uid,'213','214','n-1'))-abs(sumAll(cr,uid,'2813','2814','n-1'))-abs(sumAll(cr,uid,'2913','2914','n-1') )",
        'RN_A2_10_1':"abs(sumAll(cr,uid,'215','217','n') )",'RN_A2_10_2':"abs(sumAll(cr,uid,'2815','2817','n'))+abs(sumAll(cr,uid,'2915','2917','n') )",
        'RN_ZCL_10':"abs( diffOfVar(cr,uid,'RN_A2_10_xx',1,2))",'RN_A2_10_3':"abs(sumAll(cr,uid,'215','217','n-1'))-abs(sumAll(cr,uid,'2815','2817','n-1'))+abs(sumAll(cr,uid,'2915','2917','n-1') )",
        'RN_A2_11_1':"abs(sumAll(cr,uid,'218','229','n') )",'RN_A2_11_2':"abs(sumAll(cr,uid,'2818','2829','n'))+abs(sumAll(cr,uid,'2918','2929','n'))",
        'RN_ZCL_11':"abs( diffOfVar(cr,uid,'RN_A2_11_xx',1,2) )",'RN_A2_11_3':"abs(sumAll(cr,uid,'218','229','n-1'))- abs(sumAll(cr,uid,'2818','2829','n-1')) -abs(sumAll(cr,uid,'2918','2929','n-1') )",
        'RN_A2_12_1':"abs(sumAll(cr,uid,'230','231','n') )",'RN_A2_12_2':"abs(sumAll(cr,uid,'2930','2936','n') )",
        'RN_ZCL_12':"abs( diffOfVar(cr,uid,'RN_A2_12_xx',1,2) )",'RN_A2_12_3':"abs(sumAll(cr,uid,'230','231','n-1'))-abs(sumAll(cr,uid,'2930','2936','n-1') )",
        'RN_A2_13_1':"abs(sumAll(cr,uid,'238','259','n') )",'RN_A2_13_2':"abs(sumAll(cr,uid,'2838','2899','n'))+abs(sumAll(cr,uid,'2938','2959','n') )",
        'RN_ZCL_13':"abs( diffOfVar(cr,uid,'RN_A2_13_xx',1,2) )",'RN_A2_13_3':"abs(sumAll(cr,uid,'238','259','n-1'))-abs(sumAll(cr,uid,'2838','2899','n-1'))-abs(sumAll(cr,uid,'2938','2959','n-1') )",
        'RN_A2_14_1':"abs(sumAll(cr,uid,'262','262','n') )",'RN_A2_14_2':"abs(sumAll(cr,uid,'2962','2962','n') )",
        'RN_ZCL_14':"abs( diffOfVar(cr,uid,'RN_A2_14_xx',1,2) )",'RN_A2_14_3':"abs(sumAll(cr,uid,'262','262','n-1'))-abs(sumAll(cr,uid,'2962','2962','n-1') )",
        'RN_A2_15_1':"abs(sumAll(cr,uid,'260','261','n'))+abs(sumAll(cr,uid,'263','266','n') )",'RN_A2_15_2':"abs(sumAll(cr,uid,'2960','2961','n'))+abs(sumAll(cr,uid,'2963','2966','n') )",
        'RN_ZCL_15':"abs( diffOfVar(cr,uid,'RN_A2_15_xx',1,2) )",
        'RN_A2_15_3':"abs(sumAll(cr,uid,'260','261','n-1'))+abs(sumAll(cr,uid,'263','266','n-1'))-abs(sumAll(cr,uid,'2960','2961','n-1'))-abs(sumAll(cr,uid,'2963','2966','n-1') )",
        'RN_A2_16_1':"abs(sumAll(cr,uid,'267','268','n') )",
        'RN_A2_16_2':"abs(sumAll(cr,uid,'2967','2969','n') )",
        'RN_ZCL_16':"abs( diffOfVar(cr,uid,'RN_A2_16_xx',1,2) )",
        'RN_A2_16_3':"abs(sumAll(cr,uid,'267','268','n-1'))-abs(sumAll(cr,uid,'2967','2969','n-1') )",
        'RN_A2_17_1':"abs(sumAll(cr,uid,'270','273','n') )",
        'RN_A2_17_2':"abs(sumAll(cr,uid,'2970','2973','n') )",
        'RN_ZCL_17':"abs( diffOfVar(cr,uid,'RN_A2_17_xx',1,2) )",
        'RN_A2_17_3':"abs(sumAll(cr,uid,'270','273','n-1'))-abs(sumAll(cr,uid,'2970','2973','n-1') )",
        'RN_A2_18_1':"abs(sumAll(cr,uid,'274','274','n') )",
        'RN_A2_18_2':"abs(sumAll(cr,uid,'2974','2974','n') )",
        'RN_ZCL_18':"abs( diffOfVar(cr,uid,'RN_A2_18_xx',1,2) )",
        'RN_A2_18_3':"abs(sumAll(cr,uid,'274','274','n-1'))-abs(sumAll(cr,uid,'2974','2974','n-1') )",
        'RN_A2_19_1':"abs(sumAll(cr,uid,'275','278','n') )",
        'RN_A2_19_2':"abs(sumAll(cr,uid,'2975','2999','n') )",
        'RN_ZCL_19':"abs( diffOfVar(cr,uid,'RN_A2_19_xx',1,2) )",
        'RN_A2_19_3':"abs(sumAll(cr,uid,'275','278','n-1'))-abs(sumAll(cr,uid,'2975','2999','n-1') )",
        'RN_ZCL_20':"abs(sumOfVar(cr,uid,'RN_A2_xx_1',1,19) )",
        'RN_ZCL_22':"abs(sumOfVar(cr,uid,'RN_A2_xx_2',2,19) )",
        'RN_ZCL_23':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',1,19) )",
        'RN_ZCL_24':"abs(sumAll(cr,uid,'109','109','n-1'))+abs(sumOfVar(cr,uid,'RN_A2_xx_3',2,19) )",
        'RN_A3_1_1':"abs(sumAll(cr,uid,'30','32','n') )",
        'RN_A3_1_2':"abs(sumAll(cr,uid,'390','392','n') )",
        'RN_ZCL_25':"abs( diffOfVar(cr,uid,'RN_A3_1_xx',1,2) )",
        'RN_A3_1_3':"abs(sumAll(cr,uid,'30','32','n-1'))-abs(sumAll(cr,uid,'390','392','n-1') )",
        'RN_A3_2_1':"abs(sumAll(cr,uid,'33','33','n') )",
        'RN_A3_2_2':"abs(sumAll(cr,uid,'393','393','n') )",
        'RN_ZCL_26':"abs( diffOfVar(cr,uid,'RN_A3_2_xx',1,2) )",
        'RN_A3_2_3':"abs(sumAll(cr,uid,'33','33','n-1'))-abs(sumAll(cr,uid,'393','393','n-1') )",
        'RN_A3_3_1':"abs(sumAll(cr,uid,'34','34','n') )",
        'RN_A3_3_2':"abs(sumAll(cr,uid,'394','394','n') )",
        'RN_ZCL_27':"abs( diffOfVar(cr,uid,'RN_A3_3_xx',1,2) )",
        'RN_A3_3_3':"abs(sumAll(cr,uid,'34','34','n-1'))-abs(sumAll(cr,uid,'394','394','n-1') )",
        'RN_A3_4_1':"abs(sumAll(cr,uid,'35','36','n') )",
        'RN_A3_4_2':"abs(sumAll(cr,uid,'395','396','n') )",
        'RN_ZCL_28':"abs( diffOfVar(cr,uid,'RN_A3_4_xx',1,2) )",
        'RN_A3_4_3':"abs(sumAll(cr,uid,'35','36','n-1'))-abs(sumAll(cr,uid,'395','396','n-1') )",
        'RN_A3_5_1':"abs(sumAll(cr,uid,'37','38','n') )",
        'RN_A3_5_2':"abs(sumAll(cr,uid,'397','399','n') )",
        'RN_ZCL_29':"abs( diffOfVar(cr,uid,'RN_A3_5_xx',1,2) )",
        'RN_A3_5_3':"abs(sumAll(cr,uid,'37','38','n-1'))-abs(sumAll(cr,uid,'397','399','n-1') )",
        'RN_A3_6_1':"abs(sumAll(cr,uid,'4090','4095','n') )",
        'RN_A3_6_2':"abs(sumAll(cr,uid,'490','490','n') )",
        'RN_ZCL_30':"abs( diffOfVar(cr,uid,'RN_A3_6_xx',1,2) )",
        'RN_A3_6_3':"abs(sumAll(cr,uid,'4090','4095','n-1'))-abs(sumAll(cr,uid,'490','490','n-1') )",
        'RN_A3_7_1':"abs(sumDebtor(cr,uid,'410','418','n') )",
        'RN_A3_7_2':"abs(sumAll(cr,uid,'491','494','n') )",
        'RN_ZCL_31 ':"abs( diffOfVar(cr,uid,'RN_A3_7_xx',1,2) )",
        'RN_A3_7_3':"abs(sumDebtor(cr,uid,'410','418','n-1'))-abs(sumAll(cr,uid,'491','494','n-1') )",
        'RN_A3_8_1':"abs(sumDebtor(cr,uid,'400','408','n'))-abs(sumAll(cr,uid,'4096','4099','n'))+abs(sumDebtor(cr,uid,'420','426','n'))+abs(sumAll(cr,uid,'4287','4299','n'))+abs(sumDebtor(cr,uid,'43','43','n'))+abs(sumDebtor(cr,uid,'44','44','n'))+abs(sumDebtor(cr,uid,'450','453','n'))+abs(sumDebtor(cr,uid,'4550','4561','n'))+abs(sumDebtor(cr,uid,'4563','4599','n'))-abs(sumAll(cr,uid,'460','463','n'))-abs(sumAll(cr,uid,'465','466','n'))+abs(sumDebtor(cr,uid,'467','467','n'))+abs(sumDebtor(cr,uid,'4687','4699','n'))+abs(sumDebtor(cr,uid,'470','475','n'))+abs(sumDebtor(cr,uid,'478','479','n') )",
        'RN_A3_8_2':"abs(sumAll(cr,uid,'495','499','n') )",
        'RN_ZCL_32':"abs( diffOfVar(cr,uid,'RN_A3_8_xx',1,2) )",
        'RN_A3_8_3':"abs(sumDebtor(cr,uid,'400','408','n-1'))-abs(sumAll(cr,uid,'4096','4099','n-1'))+abs(sumDebtor(cr,uid,'420','426','n-1'))+abs(sumAll(cr,uid,'4287','4299','n-1'))+abs(sumDebtor(cr,uid,'43','43','n-1'))+abs(sumDebtor(cr,uid,'44','44','n-1'))+abs(sumDebtor(cr,uid,'450','453','n-1'))+abs(sumDebtor(cr,uid,'4550','4561','n-1'))+abs(sumDebtor(cr,uid,'4563','4599','n-1'))-abs(sumAll(cr,uid,'460','463','n-1'))-abs(sumAll(cr,uid,'465','466','n-1'))+abs(sumDebtor(cr,uid,'467','467','n-1'))+abs(sumDebtor(cr,uid,'4687','4699','n-1'))+abs(sumDebtor(cr,uid,'470','475','n-1'))+abs(sumDebtor(cr,uid,'478','479','n-1'))",
        'RN_A3_9_1':"abs(sumDebtor(cr,uid,'4562','4562','n') )",
        'RN_A3_9_2':"abs(0 )",
        'RN_ZCL_33':"abs( diffOfVar(cr,uid,'RN_A3_9_xx',1,2) )",
        'RN_A3_9_3':"abs(sumDebtor(cr,uid,'4562','4562','n-1') )",
        'RN_A3_10_1':"abs(sumAll(cr,uid,'500','508','n') )",
        'RN_A3_10_2':"abs(sumAll(cr,uid,'59','59','n') )",
        'RN_ZCL_34':"abs( diffOfVar(cr,uid,'RN_A3_10_xx',1,2) )",
        'RN_A3_10_3':"abs(sumAll(cr,uid,'500','508','n-1'))-abs(sumAll(cr,uid,'59','59','n-1') )",
        'RN_A3_11_1':"abs(sumAll(cr,uid,'510','511','n'))+abs(sumDebtor(cr,uid,'512','514','n'))+abs(sumAll(cr,uid,'515','516','n'))+abs(sumDebtor(cr,uid,'517','517','n'))+abs(sumAll(cr,uid,'5187','5189','n'))+abs(sumAll(cr,uid,'52','58','n') )",
        'RN_A3_11_2':"abs(0 )",
        'RN_ZCL_35':"abs( diffOfVar(cr,uid,'RN_A3_11_xx',1,2) )",
        'RN_A3_11_3':"abs(sumAll(cr,uid,'510','511','n-1'))+abs(sumDebtor(cr,uid,'512','514','n-1'))+abs(sumAll(cr,uid,'515','516','n-1'))+abs(sumDebtor(cr,uid,'517','517','n-1'))+abs(sumAll(cr,uid,'5187','5189','n-1'))+abs(sumAll(cr,uid,'52','58','n-1') )",
        'RN_A3_12_1':"abs(sumAll(cr,uid,'486','486','n'))+abs(sumAll(cr,uid,'4886','4886','n') )",
        'RN_A3_12_2':"abs(0 )",
        'RN_ZCL_36':"abs( diffOfVar(cr,uid,'RN_A3_1_xx',1,2) )",
        'RN_A3_12_3':"abs(sumAll(cr,uid,'486','486','n-1'))+abs(sumAll(cr,uid,'4886','4886','n-1') )",
        'RN_ZCL_37':"abs(sumOfVar(cr,uid,'RN_A3_xx_1',1,12) )",
        'RN_ZCL_38':"abs(sumOfVar(cr,uid,'RN_A3_xx_2',1,12) )",
        'RN_ZCL_39':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',25,36) )",
        'RN_ZCL_40':"abs(sumOfVar(cr,uid,'RN_A3_xx_3',1,12) )",
        'RN_A4_1_1':"abs(sumAll(cr,uid,'480','485','n') )",
        'RN_ZCL_41':"abs(sumAll(cr,uid,'480','485','n') )",
        'RN_A4_1_2':"abs(sumAll(cr,uid,'480','485','n-1') )",
        'RN_A4_2_1':"abs(sumAll(cr,uid,'169','169','n') )",
        'RN_ZCL_42':"abs(sumAll(cr,uid,'169','169','n') )",
        'RN_A4_2_2':"abs(sumAll(cr,uid,'169','169','n-1') )",
        'RN_A4_3_1':"abs(sumAll(cr,uid,'476','476','n') )",
        'RN_ZCL_43':"abs(sumAll(cr,uid,'476','476','n') )",
        'RN_A4_3_2':"abs(sumAll(cr,uid,'476','476','n-1') )",
        'RN_ZCL_44':"abs(sumOfVar(cr,uid,'RN_A4_xx_1',1,3)) +abs(sumOfVar(cr,uid,'RN_A2_xx_1',1,1)) + abs(sumOfVar(cr,uid,'RN_ZCL_xx',20,20)) + abs(sumOfVar(cr,uid,'RN_ZCL_xx',37,37) )",
        'RN_ZCL_45':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',22,22)) +abs(sumOfVar(cr,uid,'RN_ZCL_xx',38,38))",
        'RN_ZCL_46':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',1,1)) +abs(sumOfVar(cr,uid,'RN_ZCL_xx',23,23)) +abs(sumOfVar(cr,uid,'RN_ZCL_xx',39,39)) +abs(sumOfVar(cr,uid,'RN_ZCL_xx',41,43) )",
        'RN_ZCL_47':"abs(sumOfVar(cr,uid,'RN_A2_xx_2',1,1)) + abs(sumOfVar(cr,uid,'RN_ZCL_xx',24,24)) +abs(sumOfVar(cr,uid,'RN_ZCL_xx',40,40)) +abs(sumOfVar(cr,uid,'RN_A4_xx_2',1,3) )",
        'RN_A5_1_1':"abs(sumAll(cr,uid,'206','206','n') )",
        'RN_A5_2_1':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_A5_1_2':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_A5_2_2':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_A5_1_3':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_A5_2_3':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_B1_1_3':"abs(sumAll(cr,uid,'1013','1013','n'))",
        'RN_B1_1_1':"abs(sumAll(cr,uid,'100','103','n'))+abs(sumAll(cr,uid,'108','108','n') )",
        'RN_B1_1_2':"abs(sumAll(cr,uid,'100','103','n-1'))+abs(sumAll(cr,uid,'108','108','n-1') )",
        'RN_B1_2_1':"abs(sumAll(cr,uid,'104','104','n') )",
        'RN_B1_2_2':"abs(sumAll(cr,uid,'104','104','n-1') )",
        'RN_B1_3_1':"abs(sumAll(cr,uid,'105','105','n'))+abs(sumAll(cr,uid,'107','107','n') )",
        'RN_B1_3_2':"abs(sumAll(cr,uid,'105','105','n-1'))+abs(sumAll(cr,uid,'107','107','n-1') )",
        'RN_B1_3_3':"abs(sumAll(cr,uid,'107','107','n-1') )",
        'RN_B1_4_1':"abs(sumAll(cr,uid,'1060','1061','n') )",
        'RN_B1_4_2':"abs(sumAll(cr,uid,'1060','1061','n-1') )",
        'RN_B1_5_1':"abs(sumAll(cr,uid,'1063','1063','n') )",
        'RN_B1_5_2':"abs(sumAll(cr,uid,'1063','1063','n-1') )",
        'RN_B1_6_1':"abs(sumAll(cr,uid,'1062','1062','n'))+abs(sumAll(cr,uid,'1064','1067','n') )",
        'RN_B1_6_2':"abs(sumAll(cr,uid,'1062','1062','n-1'))+abs(sumAll(cr,uid,'1064','1067','n-1') )",
        'RN_B1_6_3':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_B1_7_1':"abs(sumAll(cr,uid,'1068','1079','n') )",
        'RN_B1_7_2':"abs(sumAll(cr,uid,'1068','1079','n-1') )",
        'RN_B1_7_3':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_B1_8_1':"-(sumAll(cr,uid,'11','11','n'))",
        'RN_B1_8_2':"-(sumAll(cr,uid,'11','11','n-1'))",
        'RN_ZCL_47bis':"abs(sumAll(cr,uid,'7','7','n')) -abs(sumAll(cr,uid,'6','6','n')) + abs(sumCreditor(cr,uid,'120','120','n')) - abs(sumDebtor(cr,uid,'120','120','n'))",
        'RN_ZCL_47ter':"abs(sumAll(cr,uid,'7','7','n-1')) -abs(sumAll(cr,uid,'6','6','n-1')) + abs(sumCreditor(cr,uid,'120','120','n-1')) - abs(sumDebtor(cr,uid,'120','120','n-1'))",
        'RN_B1_10_1':"abs(sumAll(cr,uid,'13','13','n') )",
        'RN_B1_10_2':"abs(sumAll(cr,uid,'13','13','n-1') )",
        'RN_B1_11_1':"abs(sumAll(cr,uid,'14','14','n') )",
        'RN_B1_11_2':"abs(sumAll(cr,uid,'14','14','n-1') )",
        'RN_ZCL_48':"abs(sumOfVar(cr,uid,'RN_B1_xx_1',1,11))+abs(sumOfVar(cr,uid,'RN_ZCL_xxbis',47,47) )",
        'RN_ZCL_49':"abs(sumOfVar(cr,uid,'RN_B1_xx_2',1,11))+abs(sumOfVar(cr,uid,'RN_ZCL_xxter',47,47) )",
        'RN_B1_12_1':"abs(sumAll(cr,uid,'1670','1673','n') )",
        'RN_B1_12_2':"abs(sumAll(cr,uid,'1670','1673','n-1') )",
        'RN_B1_13_1':"abs(sumAll(cr,uid,'1674','1674','n') )",
        'RN_B1_13_2':"abs(sumAll(cr,uid,'1674','1674','n-1') )",
        'RN_ZCL_50':"abs(sumOfVar(cr,uid,'RN_xx_1',12,13) )",
        'RN_ZCL_51':"abs(sumOfVar(cr,uid,'RN_xx_2',12,13) )",
        'RN_B1_14_1':"abs(sumAll(cr,uid,'150','152','n') )",
        'RN_B1_14_2':"abs(sumAll(cr,uid,'150','152','n-1') )",
        'RN_B1_15_1':"abs(sumAll(cr,uid,'153','159','n') )",
        'RN_B1_15_2':"abs(sumAll(cr,uid,'153','159','n-1') )",
        'RN_ZCL_52':"abs(sumOfVar(cr,uid,'RN_B1_xx_1',14,15) )",
        'RN_ZCL_53':"abs(sumOfVar(cr,uid,'RN_B1_xx_2',14,15) )",
        'RN_B1_16_1':"abs(sumAll(cr,uid,'160','162','n'))+abs(sumAll(cr,uid,'16880','16882','n') )",
        'RN_B1_16_2':"abs(sumAll(cr,uid,'160','162','n-1'))+abs(sumAll(cr,uid,'16880','16882','n-1') )",
        'RN_B1_17_1':"abs(sumAll(cr,uid,'163','163','n'))+abs(sumAll(cr,uid,'16883','16883','n') )",
        'RN_B1_17_2':"abs(sumAll(cr,uid,'163','163','n-1'))+abs(sumAll(cr,uid,'16883','16883','n-1') )",
        'RN_B1_18_1':"abs(sumAll(cr,uid,'164','164','n'))+abs(sumAll(cr,uid,'16884','16884','n'))+abs(sumCreditor(cr,uid,'512','514','n'))+abs(sumCreditor(cr,uid,'517','517','n'))+abs(sumAll(cr,uid,'5180','5186','n'))+abs(sumAll(cr,uid,'519','519','n') )",
        'RN_B1_18_2':"abs(sumAll(cr,uid,'164','164','n-1'))+abs(sumAll(cr,uid,'16884','16884','n-1'))+abs(sumCreditor(cr,uid,'512','514','n-1'))+abs(sumCreditor(cr,uid,'517','517','n-1'))+abs(sumAll(cr,uid,'5180','5186','n-1'))+abs(sumAll(cr,uid,'519','519','n-1') )",
        'RN_B1_19_1':"abs(sumAll(cr,uid,'165','165','n'))+abs(sumAll(cr,uid,'166','166','n'))+abs(sumAll(cr,uid,'1675','1687','n'))+abs(sumAll(cr,uid,'16885','16885','n'))+abs(sumAll(cr,uid,'16886','16899','n'))+abs(sumCreditor(cr,uid,'455','459','n'))+abs(sumAll(cr,uid,'17','19','n') )",
        'RN_B1_19_2':"abs(sumAll(cr,uid,'165','165','n-1'))+abs(sumAll(cr,uid,'166','166','n-1'))+abs(sumAll(cr,uid,'1675','1687','n-1'))+abs(sumAll(cr,uid,'16885','16885','n-1'))+abs(sumAll(cr,uid,'16886','16899','n-1'))+abs(sumCreditor(cr,uid,'455','459','n-1'))+abs(sumAll(cr,uid,'17','19','n-1') )",
        'RN_B1_19_3':"abs(sumAll(cr,uid,'1675','1675','n') )",
        'RN_B1_20_1':"abs(sumAll(cr,uid,'4190','4195','n') )",
        'RN_B1_20_2':"abs(sumAll(cr,uid,'4190','4195','n-1') )",
        'RN_B1_21_1':"abs(sumCreditor(cr,uid,'400','403','n'))+abs(sumCreditor(cr,uid,'408','408','n'))+abs(sumCreditor(cr,uid,'4084','4087','n') )",
        'RN_B1_21_2':"abs(sumCreditor(cr,uid,'400','403','n-1'))+abs(sumCreditor(cr,uid,'408','408','n-1'))+abs(sumCreditor(cr,uid,'4084','4087','n-1') )",
        'RN_B1_22_1':"abs(sumCreditor(cr,uid,'420','425','n'))+abs(sumCreditor(cr,uid,'426','4286','n'))+abs(sumCreditor(cr,uid,'43','43','n'))+abs(sumCreditor(cr,uid,'44','44','n') )",
        'RN_B1_22_2':"abs((sumCreditor(cr,uid,'420','425','n-1'))+abs(sumCreditor(cr,uid,'426','4286','n-1'))+abs(sumCreditor(cr,uid,'43','43','n-1'))+abs(sumCreditor(cr,uid,'44','44','n-1')) )",
        'RN_B1_23_1':"abs(sumAll(cr,uid,'269','269','n'))+abs(sumAll(cr,uid,'279','279','n'))+abs(sumCreditor(cr,uid,'404','407','n'))+abs(sumCreditor(cr,uid,'4084','4087','n') )",
        'RN_B1_23_2':"abs(sumAll(cr,uid,'269','269','n-1'))+abs(sumAll(cr,uid,'279','279','n-1'))+abs(sumCreditor(cr,uid,'404','407','n-1'))+abs(sumCreditor(cr,uid,'4084','4087','n-1') )",
        'RN_B1_24_1':"abs(sumCreditor(cr,uid,'410','418','n'))+abs(sumAll(cr,uid,'4196','4199','n'))+abs(sumCreditor(cr,uid,'450','453','n'))+abs(sumAll(cr,uid,'454','454','n'))+abs(sumAll(cr,uid,'464','464','n'))+abs(sumCreditor(cr,uid,'467','467','n'))+abs(sumAll(cr,uid,'4680','4686','n'))+abs(sumCreditor(cr,uid,'470','475','n'))+abs(sumCreditor(cr,uid,'478','479','n'))+abs(sumCreditor(cr,uid,'509','509','n') )",
        'RN_B1_24_2':"abs(sumCreditor(cr,uid,'410','418','n-1'))+abs(sumAll(cr,uid,'4196','4199','n-1'))+abs(sumCreditor(cr,uid,'450','453','n-1'))+abs(sumAll(cr,uid,'454','454','n-1'))+abs(sumAll(cr,uid,'464','464','n-1'))+abs(sumCreditor(cr,uid,'467','467','n-1'))+abs(sumAll(cr,uid,'4680','4686','n-1'))+abs(sumCreditor(cr,uid,'470','475','n-1'))+abs(sumCreditor(cr,uid,'478','479','n-1'))+abs(sumCreditor(cr,uid,'509','509','n-1') )",
        'RN_B1_25_1':"abs(sumAll(cr,uid,'487','487','n'))+abs(sumAll(cr,uid,'4880','4885','n'))+abs(sumAll(cr,uid,'4887','4899','n'))",
        'RN_B1_25_2':"abs(sumAll(cr,uid,'487','487','n-1'))+abs(sumAll(cr,uid,'4880','4885','n-1'))+abs(sumAll(cr,uid,'4887','4899','n-1') )",
        'RN_ZCL_54':"abs(sumOfVar(cr,uid,'RN_B1_xx_1',16,25) )",
        'RN_ZCL_55':"abs(sumOfVar(cr,uid,'RN_B1_xx_2',16,25) )",
        'RN_B1_26_1':"abs(sumAll(cr,uid,'477','477','n') )",
        'RN_B1_26_2':"abs(sumAll(cr,uid,'477','477','n-1') )",
        'RN_ZCL_56':"abs(sumOfVar(cr,uid,'RN_B1_xx_1',1,11))+abs(sumOfVar(cr,uid,'RN_ZCL_xxbis',47,47))+abs(sumOfVar(cr,uid,'RN_xx_1',12,13))+abs(sumOfVar(cr,uid,'RN_B1_xx_1',14,15))+abs(sumOfVar(cr,uid,'RN_B1_xx_1',16,25))+abs(sumAll(cr,uid,'477','477','n') )",
        'RN_ZCL_57':"abs(sumOfVar(cr,uid,'RN_B1_xx_2',1,11))+abs(sumOfVar(cr,uid,'RN_ZCL_xxter',47,47))+abs(sumOfVar(cr,uid,'RN_xx_2',12,13))+abs(sumOfVar(cr,uid,'RN_B1_xx_2',14,15))+abs(sumOfVar(cr,uid,'RN_B1_xx_2',16,25))+abs(sumAll(cr,uid,'477','477','n-1') )",
        'RN_B1_27_1':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_B1_27_2':"abs(sumAll(cr,uid,'0','0','n-1') )",
        'RN_B1_28_1':"abs(sumAll(cr,uid,'1051','1051','n') )",
        'RN_B1_28_2':"abs(sumAll(cr,uid,'1051','1051','n-1') )",
        'RN_B1_29_1':"abs(sumAll(cr,uid,'1052','1052','n') )",
        'RN_B1_29_2':"abs(sumAll(cr,uid,'1052','1052','n-1') )",
        'RN_B1_30_1':"abs(sumAll(cr,uid,'1053','1053','n') )",
        'RN_B1_30_2':"abs(sumAll(cr,uid,'1053','1053','n-1') )",
        'RN_B1_31_1':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_B1_31_2':"abs(sumAll(cr,uid,'0','0','n-1') )",
        'RN_B1_32_1':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_B1_32_2':"abs(sumAll(cr,uid,'0','0','n-1') )",
        'RN_B1_33_1':"abs(sumCreditor(cr,uid,'512','514','n') )",
        'RN_B1_33_2':"abs(sumCreditor(cr,uid,'512','514','n-1') )",
        'RN_C1_1_1':"abs(sumAll(cr,uid,'707','707','n'))+abs(sumAll(cr,uid,'7097','7097','n') )",
        'RN_C1_1_2':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_ZCL_58':"abs(sumOfVar(cr,uid,'RN_C1_1_xx',1,2) )",
        'N_C1_1_4':"abs(sumAll(cr,uid,'707','707','n-1'))+abs(sumAll(cr,uid,'7097','7097','n-1'))+abs(sumAll(cr,uid,'0','0','n-1') )",
        'RN_C1_2_1':"abs(sumAll(cr,uid,'700','703','n'))+abs(sumAll(cr,uid,'7090','7093','n') )",
        'RN_C1_2_2':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_ZCL_59':"abs(sumOfVar(cr,uid,'RN_C1_2_xx',1,2) )",
        'RN_C1_2_4':"abs(sumAll(cr,uid,'700','703','n-1'))+abs(sumAll(cr,uid,'7090','7093','n-1'))+abs(sumAll(cr,uid,'0','0','n-1') )",
        'RN_C1_3_1':"abs(sumAll(cr,uid,'704','706','n'))+abs(sumAll(cr,uid,'708','708','n'))+abs(sumAll(cr,uid,'7095','7096','n'))+abs(sumAll(cr,uid,'7098','7099','n') )",
        'RN_C1_3_2':"abs(sumAll(cr,uid,'0','0','n') )",
        'RN_ZCL_60':"abs(sumOfVar(cr,uid,'RN_C1_3_xx',1,2) )",
        'RN_C1_3_4':"abs(sumAll(cr,uid,'704','706','n-1'))+abs(sumAll(cr,uid,'708','708','n-1'))+abs(sumAll(cr,uid,'7095','7096','n-1'))+abs(sumAll(cr,uid,'7098','7099','n-1'))+abs(sumAll(cr,uid,'0','0','n-1') )",
        'RN_ZCL_61':"abs(sumOfVar(cr,uid,'RN_C1_xx_1',1,3) )",
        'RN_ZCL_62':"abs(sumOfVar(cr,uid,'RN_C1_xx_2',1,3) )",
        'RN_ZCL_63':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',61,62) )",
        'RN_ZCL_64':"abs(sumOfVar(cr,uid,'RN_C1_xx_4',1,3) )",
        'RN_C2_1_1':"abs(sumAll(cr,uid,'71','71','n') )",
        'RN_C2_1_2':"abs(sumAll(cr,uid,'71','71','n-1') )",
        'RN_C2_2_1':"abs(sumAll(cr,uid,'72','72','n') )",
        'RN_C2_2_2':"abs(sumAll(cr,uid,'72','72','n-1') )",
        'RN_C2_3_1':"abs(sumAll(cr,uid,'74','74','n') )",
        'RN_C2_3_2':"abs(sumAll(cr,uid,'74','74','n-1') )",
        'RN_C2_4_1':"abs(sumAll(cr,uid,'780','785','n'))+abs(sumAll(cr,uid,'790','795','n') )",
        'RN_C2_4_2':"abs(sumAll(cr,uid,'780','785','n-1'))+abs(sumAll(cr,uid,'790','795','n-1') )",
        'RN_C2_5_1':"abs(sumAll(cr,uid,'73','73','n'))+abs(sumAll(cr,uid,'750','754','n'))+abs(sumAll(cr,uid,'756','759','n') )",
        'RN_C2_5_2':"abs(sumAll(cr,uid,'73','73','n-1'))+abs(sumAll(cr,uid,'750','754','n-1'))+abs(sumAll(cr,uid,'756','759','n-1') )",
        'RN_ZCL_65':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',63,63))+abs(sumOfVar(cr,uid,'RN_C2_xx_1',1,5) )",
        'RN_ZCL_66':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',64,64))+abs(sumOfVar(cr,uid,'RN_C2_xx_2',1,5) )",
        'RN_C3_1_1':"abs(sumAll(cr,uid,'607','608','n'))+abs(sumAll(cr,uid,'6097','6097','n') )",
        'RN_C3_1_2':"abs(sumAll(cr,uid,'607','608','n-1'))+abs(sumAll(cr,uid,'6097','6097','n-1') )",
        'RN_C3_2_1':"sumAll(cr,uid,'6037','6039','n')",
        'RN_C3_2_2':"sumAll(cr,uid,'6037','6039','n-1')",
        'RN_C3_3_1':"-sumAll(cr,uid,'600','602','n') + sumAll(cr,uid,'6090','6092','n')",
        'RN_C3_3_2':"-sumAll(cr,uid,'600','602','n-1') + sumAll(cr,uid,'6090','6092','n-1')",
        'RN_C3_4_1':"sumAll(cr,uid,'6030','6036','n')",
        'RN_C3_4_2':"sumAll(cr,uid,'6030','6036','n-1')",
        'RN_C3_5_1':"abs(sumAll(cr,uid,'604','606','n') + sumAll(cr,uid,'6093','6096','n') + sumAll(cr,uid,'6098','6099','n') + sumAll(cr,uid,'61','62','n') )",
        'RN_C3_5_2':"abs(sumAll(cr,uid,'604','606','n-1') + sumAll(cr,uid,'6093','6096','n-1') + sumAll(cr,uid,'6098','6099','n-1') + sumAll(cr,uid,'61','62','n-1') )",
        'RN_C3_6_1':"abs(sumAll(cr,uid,'63','63','n') )",
        'RN_C3_6_2':"abs(sumAll(cr,uid,'63','63','n-1') )",
        'RN_C3_7_1':"abs(sumAll(cr,uid,'640','644','n') )",
        'RN_C3_7_2':"abs(sumAll(cr,uid,'640','644','n-1') )",
        'RN_C3_8_1':"abs(sumAll(cr,uid,'645','647','n'))+abs(sumAll(cr,uid,'648','649','n') )",
        'RN_C3_8_2':"abs(sumAll(cr,uid,'645','647','n-1'))+abs(sumAll(cr,uid,'648','649','n-1') )",
        'RN_C3_9_1':"abs(sumAll(cr,uid,'6800','6814','n') )",
        'RN_C3_9_2':"abs(sumAll(cr,uid,'6800','6814','n-1') )",
        'RN_C3_10_1':"abs(sumAll(cr,uid,'6816','6816','n') )",
        'RN_C3_10_2':"abs(sumAll(cr,uid,'6816','6816','n-1') )",
        'RN_C3_11_1':"abs(sumAll(cr,uid,'6817','6859','n') )",
        'RN_C3_11_2':"abs(sumAll(cr,uid,'6817','6859','n-1') )",
        'RN_C3_12_1':"abs(sumAll(cr,uid,'6815','6615','n'))",
        'RN_C3_12_2':"abs(sumAll(cr,uid,'6815','6615','n-1') )",
        'RN_C3_13_1':"abs(sumAll(cr,uid,'650','654','n'))+abs(sumAll(cr,uid,'656','659','n') )",
        'RN_C3_13_2':"abs(sumAll(cr,uid,'650','654','n-1'))+abs(sumAll(cr,uid,'656','659','n-1') )",
        'RN_ZCL_67':"abs(sumOfVar(cr,uid,'RN_C3_xx_1',1,13) )",
        'RN_ZCL_68':"abs(sumOfVar(cr,uid,'RN_C3_xx_2',1,13) )",
        'RN_ZCL_69':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',63,63))+abs(sumOfVar(cr,uid,'RN_C2_xx_1',1,5))-abs(sumOfVar(cr,uid,'RN_C3_xx_1',1,13) )",
        'RN_ZCL_70':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',64,64))+abs(sumOfVar(cr,uid,'RN_C2_xx_2',1,5))-abs(sumOfVar(cr,uid,'RN_C3_xx_2',1,13) )",
        'RN_C4_1_1':"abs(sumAll(cr,uid,'755','755','n') )",
        'RN_C4_1_2':"abs(sumAll(cr,uid,'755','755','n-1') )",
        'RN_C4_2_1':"abs(sumAll(cr,uid,'655','655','n') )",
        'RN_C4_2_2':"abs(sumAll(cr,uid,'655','655','n-1') )",
        'RN_C4_3_1':"abs(sumAll(cr,uid,'761','761','n') )",
        'RN_C4_3_2':"abs(sumAll(cr,uid,'761','761','n-1') )",
        'RN_C4_4_1':"abs(sumAll(cr,uid,'762','762','n') )",
        'RN_C4_4_2':"abs(sumAll(cr,uid,'762','762','n-1') )",
        'RN_C4_5_1':"abs(sumAll(cr,uid,'763','765','n'))+abs(sumAll(cr,uid,'768','769','n') )",
        'RN_C4_5_2':"abs(sumAll(cr,uid,'763','765','n-1'))+abs(sumAll(cr,uid,'768','769','n-1') )",
        'RN_C4_6_1':"abs(sumAll(cr,uid,'786','786','n'))+abs(sumAll(cr,uid,'796','796','n') )",
        'RN_C4_6_2':"abs(sumAll(cr,uid,'786','786','n-1'))+abs(sumAll(cr,uid,'796','796','n-1') )",
        'RN_C4_7_1':"abs(sumAll(cr,uid,'766','766','n'))",
        'RN_C4_7_2':"abs(sumAll(cr,uid,'766','766','n-1') )",
        'RN_C4_8_1':"abs(sumAll(cr,uid,'767','767','n') )",
        'RN_C4_8_2':"abs(sumAll(cr,uid,'767','767','n-1') )",
        'RN_ZCL_71':"abs(sumOfVar(cr,uid,'RN_C4_xx_1',3,8) )",
        'RN_ZCL_72':"abs(sumOfVar(cr,uid,'RN_C4_xx_2',3,8) )",
        'RN_C5_1_1':"abs(sumAll(cr,uid,'686','686','n') )",
        'RN_C5_1_2':"abs(sumAll(cr,uid,'686','686','n-1') )",
        'RN_C5_2_1':"abs(sumAll(cr,uid,'660','665','n'))+abs(sumAll(cr,uid,'668','669','n') )",
        'RN_C5_2_2':"abs(sumAll(cr,uid,'660','665','n-1'))+abs(sumAll(cr,uid,'668','669','n-1') )",
        'RN_C5_3_1':"abs(sumAll(cr,uid,'666','666','n') )",
        'RN_C5_3_2':"abs(sumAll(cr,uid,'666','666','n-1') )",
        'RN_C5_4_1':"abs(sumAll(cr,uid,'667','667','n') )",
        'RN_C5_4_2':"abs(sumAll(cr,uid,'667','667','n-1') )",
        'RN_ZCL_73':"abs(sumOfVar(cr,uid,'RN_C5_xx_1',1,4) )",
        'RN_ZCL_74':"abs(sumOfVar(cr,uid,'RN_C5_xx_2',1,4) )",
        'RN_ZCL_75':"sumOfVar(cr,uid,'RN_C4_xx_1',3,8)-sumOfVar(cr,uid,'RN_C5_xx_1',1,4)",
        'RN_ZCL_76':"sumOfVar(cr,uid,'RN_C4_xx_2',3,8)-sumOfVar(cr,uid,'RN_C5_xx_2',1,4)",
        'RN_ZCL_77':"sumOfVar(cr,uid,'RN_ZCL_xx',65,65) - sumOfVar(cr,uid,'RN_ZCL_xx',67,67) + sumAll(cr,uid,'755','755','n') - sumAll(cr,uid,'655','655','n') + sumOfVar(cr,uid,'RN_ZCL_xx',71,71) - sumOfVar(cr,uid,'RN_ZCL_xx',73,73)",
        'RN_ZCL_78':"sumOfVar(cr,uid,'RN_ZCL_xx',66,66) - sumOfVar(cr,uid,'RN_ZCL_xx',68,68) + sumAll(cr,uid,'755','755','n-1') - sumAll(cr,uid,'655','655','n-1') + sumOfVar(cr,uid,'RN_ZCL_xx',72,72) - sumOfVar(cr,uid,'RN_ZCL_xx',74,74)",
        'RN_D1_1_1':"abs(sumAll(cr,uid,'770','774','n') )",
        'RN_D1_1_2':"abs(sumAll(cr,uid,'770','774','n-1') )",
        'RN_D1_2_1':"abs(sumAll(cr,uid,'775','779','n') )",
        'RN_D1_2_2':"abs(sumAll(cr,uid,'775','779','n-1') )",
        'RN_D1_3_1':"abs(sumAll(cr,uid,'787','789','n'))+abs(sumAll(cr,uid,'797','799','n') )",
        'RN_D1_3_2':"abs(sumAll(cr,uid,'787','789','n-1'))+abs(sumAll(cr,uid,'797','799','n-1') )",
        'RN_ZCL_79':"abs(sumOfVar(cr,uid,'RN_D1_xx_1',1,3) )",
        'RN_ZCL_80':"abs(sumOfVar(cr,uid,'RN_D1_xx_2',1,3) )",
        'RN_D1_4_1':"abs(sumAll(cr,uid,'670','674','n') )",
        'RN_D1_4_2':"abs(sumAll(cr,uid,'670','674','n-1') )",
        'RN_D1_5_1':"abs(sumAll(cr,uid,'675','679','n') )",
        'RN_D1_5_2':"abs(sumAll(cr,uid,'675','679','n-1') )",
        'RN_D1_6_1':"abs(sumAll(cr,uid,'687','689','n') )",
        'RN_D1_6_2':"abs(sumAll(cr,uid,'687','689','n-1') )",
        'RN_ZCL_81':"abs(sumOfVar(cr,uid,'RN_D1_xx_1',4,6) )",
        'RN_ZCL_82':"abs(sumOfVar(cr,uid,'RN_D1_xx_2',4,6) )",
        'RN_ZCL_83':"sumOfVar(cr,uid,'RN_D1_xx_1',1,3) - sumOfVar(cr,uid,'RN_D1_xx_1',4,6)",
        'RN_ZCL_84':"sumOfVar(cr,uid,'RN_D1_xx_2',1,3) - sumOfVar(cr,uid,'RN_D1_xx_2',4,6)",
        'RN_D1_7_1':"abs(sumAll(cr,uid,'690','694','n') )",
        'RN_D1_7_2':"abs(sumAll(cr,uid,'690','694','n-1') )",
        'RN_D1_8_1':"sumAll(cr,uid,'695','699','n') " ,
        'RN_D1_8_2':"sumAll(cr,uid,'695','699','n-1')",
        'RN_ZCL_85':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',65,65) + sumOfVar(cr,uid,'RN_C4_xx_1',1,1) + sumOfVar(cr,uid,'RN_ZCL_xx',71,71) + sumOfVar(cr,uid,'RN_ZCL_xx',79,79) )",
        'RN_ZCL_86':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',66,66) + sumOfVar(cr,uid,'RN_C4_xx_1',1,1) + sumOfVar(cr,uid,'RN_ZCL_xx',72,72) + sumOfVar(cr,uid,'RN_ZCL_xx',80,80) )",
        'RN_ZCL_87':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',67,67) + sumOfVar(cr,uid,'RN_C4_xx_1',2,2) + sumOfVar(cr,uid,'RN_ZCL_xx',73,73) + sumOfVar(cr,uid,'RN_ZCL_xx',81,81) + sumOfVar(cr,uid,'RN_D1_xx_1',7,7) + sumOfVar(cr,uid,'RN_D1_xx_1',8,8) )",
        'RN_ZCL_88':"abs(sumOfVar(cr,uid,'RN_ZCL_xx',68,68) + sumOfVar(cr,uid,'RN_C4_xx_2',2,2) + sumOfVar(cr,uid,'RN_ZCL_xx',74,74) + sumOfVar(cr,uid,'RN_ZCL_xx',82,82) + sumOfVar(cr,uid,'RN_D1_xx_2',7,7) + sumOfVar(cr,uid,'RN_D1_xx_2',8,8) )",
        'RN_ZCL_89':"sumOfVar(cr,uid,'RN_ZCL_xx',85,85) - sumOfVar(cr,uid,'RN_ZCL_xx',87,87)",
        'RN_ZCL_90':"sumOfVar(cr,uid,'RN_ZCL_xx',86,86) - sumOfVar(cr,uid,'RN_ZCL_xx',88,88)",
        }

    key=val_dict.keys()
    key.sort()
    for k in key:
        varname = k
        vardef = val_dict[k]
        val = eval(val_dict[varname])
        mytable[varname] = float(val)
    for i in mytable:
        mytable[i] = int(mytable[i])

    mytable['DATE_CLOT_1']=start_date_year_n[3]
    mytable['DATE_CLOT_2']=start_date_year_n[2]
    mytable['DATE_CLOT_3']=start_date_year_n[1]
    mytable['DATE_CLOT_4']=start_date_year_n[0]
    mytable['DATE_CLOT_5']=start_date_year_n[6]
    mytable['DATE_CLOT_6']=start_date_year_n[5]
    mytable['DATE_CLOT_7']=start_date_year_n[9]
    mytable['DATE_CLOT_8']=start_date_year_n[8]

    mytable['IDENT_DEST_1']=company_name

    ad = tools.config['addons_path']
    fpath=ad+"/l10n_fr/wizard/fpdftemp.fdf"
    outfile=ad+"/l10n_fr/wizard/2050x.pdf"
    fpdftemp = open(fpath,"w")
    write_fields(fpdftemp,mytable)
    fpdftemp.close()
    import threading
    def pr_report(self):
        os.system('evince output.pdf')
    os.system('pdftk %s fill_form %s output output.pdf flatten'% (outfile,fpath))
    report_th = threading.Thread(target=pr_report, args=('a'))
    report_th.start()
#    os.system('evince output.pdf')
    return {}


def _get_defaults(self, cr, uid, data, context):
    fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')
    data['form']['fiscalyear'] = fiscalyear_obj.find(cr, uid)

    user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid, context=context)
    if user.company_id:
        company_id = user.company_id.id
    else:
        company_id = pooler.get_pool(cr.dbname).get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
    data['form']['company_id'] = company_id
    return data['form']

class wizard_report(wizard.interface):

    states = {
        'init': {
                 'actions': [_get_defaults],
                 'result': {'type':'form', 'arch':_aged_trial_form, 'fields':_aged_trial_fields, 'state':[('end','Cancel'),('pdf','Print Balance Sheet')]},
                },
        'pdf': {
                'actions': [],
                'result': {'type':'action', 'action': _test, 'state':'end'},
                },
          }
wizard_report('account.chart.report')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

