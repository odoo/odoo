# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv
from osv import orm

from tools.translate import _

def _get_answers(cr, uid, ids):
    """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm profiling’s IDs """

    query = """
    select distinct(answer)
    from profile_question_yes_rel
    where profile IN %s"""

    cr.execute(query, (tuple(ids),))
    ans_yes = [x[0] for x in cr.fetchall()]

    query = """
    select distinct(answer)
    from profile_question_no_rel
    where profile IN %s"""

    cr.execute(query, (tuple(ids),))
    ans_no = [x[0] for x in cr.fetchall()]

    return [ans_yes, ans_no]


def _get_parents(cr, uid, ids):
    """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm profiling’s IDs
        @return: Get parents's Id """

    ids_to_check = ids
    cr.execute("""
     select distinct(parent_id)
     from crm_segmentation
     where parent_id is not null
     and id IN %s""",(tuple(ids),))

    parent_ids = [x[0] for x in cr.fetchall()]

    trigger = False
    for x in parent_ids:
        if x not in ids_to_check:
            ids_to_check.append(x)
            trigger = True

    if trigger:
        ids_to_check = _get_parents(cr, uid, ids_to_check)

    return ids_to_check


def test_prof(cr, uid, seg_id, pid, answers_ids = []):

    """ return True if the partner pid fetch the segmentation rule seg_id
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param seg_id: Segmentaion's ID
        @param pid: partner's ID
        @param answers_ids: Answers's IDs
    """

    ids_to_check = _get_parents(cr, uid, [seg_id])
    [yes_answers, no_answers] = _get_answers(cr, uid, ids_to_check)
    temp = True
    for y_ans in yes_answers:
        if y_ans not in answers_ids:
            temp = False
            break
    if temp:
        for ans in answers_ids:
            if ans in no_answers:
                temp = False
                break
    if temp:
        return True
    return False


def _recompute_categ(self, cr, uid, pid, answers_ids):
    """ Recompute category
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param pid: partner's ID
        @param answers_ids: Answers's IDs
    """

    ok =  []
    cr.execute('''
        select r.category_id
        from res_partner_category_rel r left join crm_segmentation s on (r.category_id = s.categ_id)
        where r.partner_id = %s and (s.exclusif = false or s.exclusif is null)
        ''', (pid,))
    for x in cr.fetchall():
        ok.append(x[0])

    query = '''
        select id, categ_id
        from crm_segmentation
        where profiling_active = true'''
    if ok != []:
        query = query +''' and categ_id not in(%s)'''% ','.join([str(i) for i in ok ])
    query = query + ''' order by id '''

    cr.execute(query)
    segm_cat_ids = cr.fetchall()

    for (segm_id, cat_id) in segm_cat_ids:
        if test_prof(cr, uid, segm_id, pid, answers_ids):
            ok.append(cat_id)
    return ok


class question(osv.osv):
    """ Question """

    _name="crm_profiling.question"
    _description= "Question"

    _columns={
        'name': fields.char("Question",size=128, required=True),
        'answers_ids': fields.one2many("crm_profiling.answer","question_id","Avalaible answers",),
        }

question()


class questionnaire(osv.osv):
    """ Questionnaire """

    _name="crm_profiling.questionnaire"
    _description= "Questionnaire"

    def build_form(self, cr, uid, data, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param data: Get Data
            @param context: A standard dictionary for contextual values """
        
        query = """
        select name, id
        from crm_profiling_question
        where id in ( select question from profile_questionnaire_quest_rel where questionnaire = %s)"""
        res = cr.execute(query, (data['form']['questionnaire_name'],))
        result = cr.fetchall()
        quest_fields={}
        quest_form='''<?xml version="1.0"?>
            <form string="%s">''' % _('Questionnaire')
        for name, oid in result:
            quest_form = quest_form + '<field name="quest_form%d"/><newline/>' % (oid,)
            quest_fields['quest_form%d' % (oid,)] = {'string': name, 'type': 'many2one', \
                        'relation': 'crm_profiling.answer', 'domain': [('question_id','=',oid)] }
        quest_form = quest_form + '''</form>'''
        return quest_form, quest_fields

    _columns = {
        'name': fields.char("Questionnaire",size=128, required=True),
        'description':fields.text("Description", required=True),
        'questions_ids': fields.many2many('crm_profiling.question','profile_questionnaire_quest_rel',\
                                'questionnaire', 'question', "Questions"),
    }

questionnaire()


class answer(osv.osv):
    _name="crm_profiling.answer"
    _description="Answer"
    _columns={
        "name": fields.char("Answer",size=128, required=True),
        "question_id": fields.many2one('crm_profiling.question',"Question"),
        }
answer()


class partner(osv.osv):
    _inherit="res.partner"
    _columns={
        "answers_ids": fields.many2many("crm_profiling.answer","partner_question_rel",\
                                "partner","answer","Answers"),
        }

    def _questionnaire_compute(self, cr, uid, data, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param data: Get Data
            @param context: A standard dictionary for contextual values """

        temp = []
        for x in data['form']:
            if x.startswith("quest_form") and data['form'][x] != 0 :
                temp.append(data['form'][x])

        query = "select answer from partner_question_rel where partner=%s"
        cr.execute(query, (data['id'],))
        for x in cr.fetchall():
            temp.append(x[0])

        self.write(cr, uid, [data['id']], {'answers_ids':[[6, 0, temp]]}, context=context)
        return {}


    def write(self, cr, uid, ids, vals, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of crm profiling’s IDs
            @param context: A standard dictionary for contextual values """

        if 'answers_ids' in vals:
            vals['category_id']=[[6, 0, _recompute_categ(self, cr, uid, ids[0], vals['answers_ids'][0][2])]]
        return super(partner, self).write(cr, uid, ids, vals, context=context)

partner()


class crm_segmentation(osv.osv):
    """ CRM Segmentation """

    _inherit="crm.segmentation"
    _columns={
        "answer_yes": fields.many2many("crm_profiling.answer","profile_question_yes_rel",\
                            "profile","answer","Included Answers"),
        "answer_no": fields.many2many("crm_profiling.answer","profile_question_no_rel",\
                            "profile","answer","Excluded Answers"),
        'parent_id': fields.many2one('crm.segmentation', 'Parent Profile'),
        'child_ids': fields.one2many('crm.segmentation', 'parent_id', 'Child Profiles'),
        'profiling_active': fields.boolean('Use The Profiling Rules', help='Check\
                             this box if you want to use this tab as part of the \
                             segmentation rule. If not checked, the criteria beneath will be ignored')
        }

    _constraints = [
        (osv.osv._check_recursion, 'Error ! You can not create recursive profiles.', ['parent_id'])
    ]

    def process_continue(self, cr, uid, ids, start=False):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of crm segmentation’s IDs """

        categs = self.read(cr,uid,ids,['categ_id','exclusif','partner_id', \
                            'sales_purchase_active', 'profiling_active'])
        for categ in categs:
            if start:
                if categ['exclusif']:
                    cr.execute('delete from res_partner_category_rel where \
                            category_id=%s', (categ['categ_id'][0],))

            id = categ['id']

            cr.execute('select id from res_partner order by id ')
            partners = [x[0] for x in cr.fetchall()]

            if categ['sales_purchase_active']:
                to_remove_list=[]
                cr.execute('select id from crm_segmentation_line where segmentation_id=%s', (id,))
                line_ids = [x[0] for x in cr.fetchall()]

                for pid in partners:
                    if (not self.pool.get('crm.segmentation.line').test(cr, uid, line_ids, pid)):
                        to_remove_list.append(pid)
                for pid in to_remove_list:
                    partners.remove(pid)

            if categ['profiling_active']:
                to_remove_list = []
                for pid in partners:

                    cr.execute('select distinct(answer) from partner_question_rel where partner=%s',(pid,))
                    answers_ids = [x[0] for x in cr.fetchall()]

                    if (not test_prof(cr, uid, id, pid, answers_ids)):
                        to_remove_list.append(pid)
                for pid in to_remove_list:
                    partners.remove(pid)

            for partner_id in partners:
                cr.execute('insert into res_partner_category_rel (category_id,partner_id) values (%s,%s)', (categ['categ_id'][0],partner_id))

            self.write(cr, uid, [id], {'state':'not running', 'partner_id':0})
        return True

crm_segmentation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

