# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

import time

from openerp import pooler, tools
from openerp.report import report_sxw
from openerp.report.interface import report_rml
from openerp.tools import to_xml

class survey_analysis(report_rml):
    def create(self, cr, uid, ids, datas, context):
        surv_obj = pooler.get_pool(cr.dbname).get('survey')
        user_obj = pooler.get_pool(cr.dbname).get('res.users')
        rml_obj=report_sxw.rml_parse(cr, uid, surv_obj._name,context)
        company=user_obj.browse(cr,uid,[uid],context)[0].company_id

        rml ="""<document filename="Survey Analysis Report.pdf">
                <template pageSize="(595.0,842.0)" title="Survey Analysis" author="OpenERP S.A.(sales@openerp.com)" allowSplitting="20">
                        <pageTemplate>
                        <frame id="first" x1="1.3cm" y1="1.5cm" width="18.4cm" height="26.5cm"/>
                        <pageGraphics>
                        <fill color="black"/>
                        <stroke color="black"/>
                        <setFont name="DejaVu Sans" size="8"/>
                        <drawString x="1.3cm" y="28.3cm"> """+to_xml(rml_obj.formatLang(time.strftime("%Y-%m-%d %H:%M:%S"),date_time=True))+"""</drawString>
                        <setFont name="DejaVu Sans Bold" size="10"/>
                        <drawString x="9.8cm" y="28.3cm">"""+ to_xml(company.name) +"""</drawString>
                        <stroke color="#000000"/>
                        <lines>1.3cm 28.1cm 20cm 28.1cm</lines>
                        </pageGraphics>
                        </pageTemplate>
                  </template>
                  <stylesheet>
                    <blockTableStyle id="Table1">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6"/>
                    </blockTableStyle>
                    <blockTableStyle id="Table2">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                    </blockTableStyle>
                    <blockTableStyle id="Table3">
                      <blockAlignment value="LEFT"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="1,0" stop="2,-1"/>
                      <blockValign value="TOP"/>
                    </blockTableStyle>
                    <blockTableStyle id="Table4">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#000000" start="0,-1" stop="1,-1"/>
                    </blockTableStyle>
                    <blockTableStyle id="Table5">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#8f8f8f" start="0,-1" stop="1,-1"/>
                    </blockTableStyle>
                    <blockTableStyle id="Table_heading">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBEFORE" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEAFTER" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEABOVE" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                    </blockTableStyle>
                    <blockTableStyle id="Table_head_2">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBEFORE" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEAFTER" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEABOVE" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                    </blockTableStyle>
                    <initialize>
                      <paraStyle name="all" alignment="justify"/>
                    </initialize>
                    <paraStyle name="answer_right" alignment="RIGHT" fontName="helvetica" fontSize="09.0" leftIndent="2.0"/>
                    <paraStyle name="Standard1" fontName="helvetica-bold" alignment="RIGHT" fontSize="09.0"/>
                    <paraStyle name="Standard" alignment="LEFT" fontName="Helvetica-Bold" fontSize="11.0"/>
                    <paraStyle name="header1" fontName="Helvetica" fontSize="11.0"/>
                    <paraStyle name="response" fontName="Helvetica-oblique" fontSize="9.5"/>
                    <paraStyle name="response-bold" fontName="Helvetica-bold" fontSize="9" alignment="RIGHT" />
                    <paraStyle name="page" fontName="helvetica" fontSize="11.0" leftIndent="0.0"/>
                    <paraStyle name="question" fontName="helvetica-boldoblique" fontSize="10.0" leftIndent="3.0"/>
                    <paraStyle name="answer_bold" fontName="Helvetica-Bold" fontSize="09.0" leftIndent="2.0"/>
                    <paraStyle name="answer" fontName="helvetica" fontSize="09.0" leftIndent="2.0"/>
                    <paraStyle name="Title" fontName="helvetica" fontSize="20.0" leading="15" spaceBefore="6.0" spaceAfter="6.0" alignment="CENTER"/>
                    <paraStyle name="terp_tblheader_General_Centre" fontName="Helvetica-Bold" fontSize="9.0" leading="10" alignment="CENTER" spaceBefore="6.0" spaceAfter="6.0"/>
                    <paraStyle name="terp_default_Centre_8" fontName="Helvetica" fontSize="9.0" leading="10" alignment="CENTER" spaceBefore="0.0" spaceAfter="0.0"/>
                    <paraStyle name="terp_default_Center_heading" fontName="Helvetica-bold" fontSize="9.0" leading="10" alignment="CENTER" spaceBefore="0.0" spaceAfter="0.0"/>
                    <paraStyle name="P2" fontName="Helvetica" fontSize="14.0" leading="15" spaceBefore="6.0" spaceAfter="6.0"/>
                  </stylesheet>
                  <images/>
                  """

        if datas.has_key('form') and datas['form']['survey_ids']:
           ids =  datas['form']['survey_ids']

        for survey in surv_obj.browse(cr, uid, ids):
            rml += """<story>
                    <para style="Title">Answers Summary</para>
                    <para style="Standard"><font></font></para>
                    <para style="P2">
                      <font color="white"> </font>
                    </para>
                    <blockTable colWidths="280.0,100.0,120.0" style="Table_heading">
                      <tr>
                        <td>
                          <para style="terp_tblheader_General_Centre">Survey Title </para>
                        </td>
                        <td>
                          <para style="terp_tblheader_General_Centre">Total Started Survey </para>
                        </td>
                        <td>
                          <para style="terp_tblheader_General_Centre">Total Completed Survey </para>
                        </td>
                      </tr>
                      </blockTable>
                      <blockTable colWidths="280.0,100.0,120.0" style="Table_head_2">
                      <tr>
                        <td>
                          <para style="terp_default_Centre_8">""" + to_xml(tools.ustr(survey.title)) + """</para>
                        </td>
                        <td>
                          <para style="terp_default_Centre_8">""" + str(survey.tot_start_survey) + """</para>
                        </td>
                        <td>
                          <para style="terp_default_Centre_8">""" + str(survey.tot_comp_survey) + """</para>
                        </td>
                      </tr>
                    </blockTable>
                    <para style="P2">
                      <font color="white"> </font>
                    </para>"""
            for page in survey.page_ids:
                rml += """ <blockTable colWidths="500" style="Table4">
                              <tr>
                                <td><para style="page">Page :- """ + to_xml(tools.ustr(page.title)) + """</para></td>
                              </tr>
                           </blockTable>"""
                for que in page.question_ids:
                    rml +="""<blockTable colWidths="500" style="Table5">
                              <tr>
                                <td><para style="question">"""  + to_xml(tools.ustr(que.question)) + """</para></td>
                              </tr>
                             </blockTable>"""
                    cols_widhts = []

                    if que.type in ['matrix_of_choices_only_one_ans','matrix_of_choices_only_multi_ans']:
                        cols_widhts.append(200)
                        for col in range(0, len(que.column_heading_ids) + 1):
                            cols_widhts.append(float(300 / (len(que.column_heading_ids) + 1)))
                        colWidths = ",".join(map(tools.ustr, cols_widhts))
                        matrix_ans = [(0,'')]

                        for col in que.column_heading_ids:
                            if col.title not in matrix_ans:
                                matrix_ans.append((col.id,col.title))
                        rml += """<blockTable colWidths=" """ + colWidths + """ " style="Table1"><tr>"""
                        for mat_col in range(0, len(matrix_ans)):
                            rml+="""<td><para style="response">""" + to_xml(tools.ustr(matrix_ans[mat_col][1])) + """</para></td>"""
                        rml += """<td><para style="response-bold">Answer Count</para></td>
                                </tr>"""
                        last_col = cols_widhts[-1]

                        for ans in que.answer_choice_ids:
                            rml += """<tr><td><para style="answer">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>"""
                            cr.execute("select count(id) from survey_response_answer sra where sra.answer_id = %s", (ans.id,))
                            tot_res = cr.fetchone()[0]
                            cr.execute("select count(id) ,sra.column_id from survey_response_answer sra where sra.answer_id=%s group by sra.column_id", (ans.id,))
                            calc_res = cr.dictfetchall()
                            for mat_col in range(1, len(matrix_ans)):
                                percantage = 0.0
                                cal_count = 0
                                for cal in calc_res:
                                    if cal['column_id'] == matrix_ans[mat_col][0]:
                                        cal_count = cal['count']
                                if tot_res:
                                    percantage = round(float(cal_count)*100 / tot_res,2)
                                if percantage:
                                    rml += """<td color="#FFF435"><para style="answer_bold">""" + tools.ustr(percantage) +"% (" + tools.ustr(cal_count) + """)</para></td>"""
                                else:
                                    rml += """<td color="#FFF435"><para style="answer">""" + tools.ustr(percantage) +"% (" + tools.ustr(cal_count) + """)</para></td>"""
                            rml += """<td><para style="answer_right">""" + tools.ustr(tot_res) + """</para></td>
                                </tr>"""
                        rml += """</blockTable>"""

                        if que.is_comment_require:
                            cr.execute("select count(id) from survey_response_line where question_id = %s and comment != ''",(que.id,))
                            tot_res = cr.fetchone()[0]
                            rml += """<blockTable colWidths=" """+ str(500 - last_col) +"," + str(last_col) + """ " style="Table1"><tr><td><para style="answer_right">""" + to_xml(tools.ustr(que.comment_label)) + """</para></td>
                                    <td><para style="answer">""" + tools.ustr(tot_res) + """</para></td></tr></blockTable>"""

                    elif que.type in['multiple_choice_only_one_ans', 'multiple_choice_multiple_ans', 'multiple_textboxes','date_and_time','date','multiple_textboxes_diff_type']:
                        rml += """<blockTable colWidths="240.0,210,50.0" style="Table1">"""
                        rml += """ <tr>
                             <td> <para style="Standard"> </para></td>
                             <td> <para style="terp_default_Center_heading">Answer Percentage</para></td>
                             <td> <para style="response-bold">Answer Count</para></td>
                         </tr>"""

                        for ans in que.answer_choice_ids:
                            progress = ans.average * 7 / 100
                            rml += """<tr><td><para style="answer">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>
                                    <td>
                                    <illustration>
                                    <stroke color="lightslategray"/>
                                       <rect x="0.1cm" y="-0.45cm" width="7.2 cm" height="0.5cm" fill="no" stroke="yes"  round="0.1cm"/>
                                       """
                            if progress:
                                rml += """<fill color="lightsteelblue"/>
                                       <rect x="0.2cm" y="-0.35cm"  width='""" + tools.ustr(str(float(progress)) +'cm') + """' height="0.3cm" fill="yes" stroke="no"  round="0.1cm"/>"""
                            rml += """
                                <fill color="black"/>
                                <setFont name="Helvetica" size="9"/>
                                <drawString x="3.2cm" y="-0.30cm">"""  + tools.ustr(ans.average) + """%</drawString></illustration>
                                    </td>
                                    <td><para style="answer_right">""" + tools.ustr(ans.response) + """</para></td></tr>"""
                        rml += """</blockTable>"""

                        if que.is_comment_require:
#                            if que.make_comment_field:
#                                cr.execute("select count(id) from survey_response_line where question_id = %s and comment != ''", (que.id,))
#                                tot_res = cr.fetchone()[0]
#                                tot_avg = 0.00
#                                if que.tot_resp:
#                                    tot_avg = round(float(tot_res * 100)/ que.tot_resp,2)
#                                rml+="""<blockTable colWidths="280.0,120,100.0" style="Table1"><tr><td><para style="answer">""" +to_xml(tools.ustr(que.comment_label)) + """</para></td>
#                                        <td><para style="answer">""" + str(tot_avg) + """%</para></td>
#                                        <td><para style="answer">""" + tools.ustr(tot_res) + """</para></td></tr></blockTable>"""
#                            else:
                            cr.execute("select count(id) from survey_response_line where question_id = %s and comment != ''", (que.id,))
                            tot_res = cr.fetchone()[0]
                            rml += """<blockTable colWidths="450.0,50.0" style="Table1"><tr><td><para style="answer_right">""" + to_xml(tools.ustr(que.comment_label)) + """</para></td>
                                    <td><para style="answer_right">""" + tools.ustr(tot_res) + """</para></td></tr></blockTable>"""

                    elif que.type in['single_textbox']:
                        cr.execute("select count(id) from survey_response_line where question_id = %s and single_text!=''",(que.id,))
                        rml += """<blockTable colWidths="400.0,100.0" style="Table1">
                             <tr>
                                 <td> <para style="Standard"> </para></td>
                                 <td> <para style="response-bold">Answer Count</para></td>
                             </tr>
                            <tr><td><para style="answer"></para></td>
                                <td><para style="answer_right">""" + tools.ustr(cr.fetchone()[0]) + """ </para></td></tr>
                            </blockTable>"""

                    elif que.type in['comment']:
                        cr.execute("select count(id) from survey_response_line where question_id = %s and comment !=''", (que.id,))
                        rml += """<blockTable colWidths="400.0,100.0" style="Table1">
                             <tr>
                                 <td> <para style="Standard"> </para></td>
                                 <td> <para style="response-bold">Answer Count</para></td>
                             </tr>
                            <tr><td><para style="answer"></para></td>
                                <td><para style="answer_right">""" + tools.ustr(cr.fetchone()[0]) + """ </para></td></tr>
                            </blockTable>"""

                    elif que.type in['rating_scale']:
                        cols_widhts.append(200)
                        for col in range(0,len(que.column_heading_ids) + 2):
                            cols_widhts.append(float(300 / (len(que.column_heading_ids) + 2)))
                        colWidths = ",".join(map(tools.ustr, cols_widhts))
                        matrix_ans = [(0,'')]

                        for col in que.column_heading_ids:
                            if col.title not in matrix_ans:
                                matrix_ans.append((col.id,col.title))
                        rml += """<blockTable colWidths=" """ + colWidths + """ " style="Table1"><tr>"""
                        for mat_col in range(0,len(matrix_ans)):
                            rml += """<td><para style="response">""" + to_xml(tools.ustr(matrix_ans[mat_col][1])) + """</para></td>"""
                        rml += """<td><para style="response-bold">Rating Average</para></td>
                                <td><para style="response-bold">Answer Count</para></td>
                                </tr>"""

                        for ans in que.answer_choice_ids:
                            rml += """<tr><td><para style="answer">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>"""
                            res_count = 0
                            rating_weight_sum = 0
                            for mat_col in range(1, len(matrix_ans)):
                                cr.execute("select count(sra.answer_id) from survey_response_line sr, survey_response_answer sra\
                                     where sr.id = sra.response_id and  sra.answer_id = %s and sra.column_id ='%s'", (ans.id,matrix_ans[mat_col][0]))
                                tot_res = cr.fetchone()[0]
                                cr.execute("select count(sra.answer_id),sqc.rating_weight from survey_response_line sr, survey_response_answer sra ,\
                                        survey_question_column_heading sqc where sr.id = sra.response_id and \
                                        sqc.question_id = sr.question_id  and sra.answer_id = %s and sqc.title ='%s'\
+                                       group by sra.answer_id,sqc.rating_weight", (ans.id,matrix_ans[mat_col][1]))
                                col_weight =  cr.fetchone()

                                if not col_weight:
                                    col_weight= (0,0)
                                elif not col_weight[1]:
                                    col_weight = (col_weight[0],0)
                                res_count = col_weight[0]

                                if tot_res and res_count:
                                    rating_weight_sum += int(col_weight[1]) * tot_res
                                    tot_per = round((float(tot_res) * 100) / int(res_count), 2)
                                else:
                                    tot_per = 0.0
                                if tot_res:
                                    rml += """<td><para style="answer_bold">""" + tools.ustr(tot_per) + "%(" + tools.ustr(tot_res) + """)</para></td>"""
                                else:
                                    rml += """<td><para style="answer">""" + tools.ustr(tot_per)+"%(" + tools.ustr(tot_res) + """)</para></td>"""

                            percantage = 0.00
                            if res_count:
                                percantage = round((float(rating_weight_sum)/res_count), 2)
                            rml += """<td><para style="answer_right">""" + tools.ustr(percantage) + """</para></td>
                                <td><para style="answer_right">""" + tools.ustr(res_count) + """</para></td></tr>"""
                        rml += """</blockTable>"""

                    elif que.type in['matrix_of_drop_down_menus']:
                        for column in que.column_heading_ids:
                            rml += """<blockTable colWidths="500" style="Table1"><tr>
                                <td><para style="answer">""" + to_xml(tools.ustr(column.title)) + """</para></td></tr></blockTable>"""
                            menu_choices = column.menu_choice.split('\n')
                            cols_widhts = []
                            cols_widhts.append(200)
                            for col in range(0, len(menu_choices) + 1):
                                cols_widhts.append(float(300 / (len(menu_choices) + 1)))
                            colWidths = ",".join(map(tools.ustr, cols_widhts))
                            rml += """<blockTable colWidths=" """ + colWidths + """ " style="Table1"><tr>
                                <td><para style="response"></para></td>"""

                            for menu in menu_choices:
                                rml += """<td><para style="response">""" + to_xml(tools.ustr(menu)) + """</para></td>"""
                            rml += """<td><para style="response-bold">Answer Count</para></td></tr>"""
                            cr.execute("select count(id), sra.answer_id from survey_response_answer sra \
                                     where sra.column_id='%s' group by sra.answer_id ", (column.id,))
                            res_count = cr.dictfetchall()
                            cr.execute("select count(sra.id),sra.value_choice, sra.answer_id, sra.column_id from survey_response_answer sra \
                                 where sra.column_id='%s' group by sra.value_choice ,sra.answer_id, sra.column_id", (column.id,))
                            calc_percantage = cr.dictfetchall()

                            for ans in que.answer_choice_ids:
                                rml += """<tr><td><para style="answer_right">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>"""
                                for mat_col in range(0, len(menu_choices)):
                                    calc = 0
                                    response = 0
                                    for res in res_count:
                                        if res['answer_id'] == ans.id: response = res['count']
                                    for per in calc_percantage:
                                        if ans.id == per['answer_id'] and menu_choices[mat_col] == per['value_choice']:
                                            calc = per['count']
                                    percantage = 0.00

                                    if calc and response:
                                        percantage = round((float(calc)* 100) / response,2)
                                    if calc:
                                        rml += """<td><para style="answer_bold">""" +tools.ustr(percantage)+"% (" +  tools.ustr(calc) + """)</para></td>"""
                                    else:
                                        rml += """<td><para style="answer">""" +tools.ustr(percantage)+"% (" +  tools.ustr(calc) + """)</para></td>"""

                                response = 0
                                for res in res_count:
                                    if res['answer_id'] == ans.id: response = res['count']
                                rml += """<td><para style="answer_right">""" + tools.ustr(response) + """</para></td></tr>"""
                            rml += """</blockTable>"""

                    elif que.type in['numerical_textboxes']:
                        rml += """<blockTable colWidths="240.0,20,100.0,70,70.0" style="Table1">
                             <tr>
                             <td> <para style="Standard"> </para></td>
                             <td> <para style="Standard"> </para></td>
                             <td> <para style="response">Answer Average</para></td>
                             <td> <para style="response">Answer Total</para></td>
                             <td> <para style="response-bold">Answer Count</para></td>
                         </tr>"""
                        for ans in que.answer_choice_ids:
                            cr.execute("select answer from survey_response_answer where answer_id=%s group by answer", (ans.id,))
                            tot_res = cr.dictfetchall()
                            total = 0
                            for  tot in tot_res:
                                total += int(tot['answer'])
                            per = 0.00

                            if len(tot_res):
                                per = round((float(total) / len(tot_res)),2)
                            rml+="""<tr><td><para style="answer">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>
                                    <td> <para style="Standard"> </para></td>
                                    <td> <para style="answer">""" + tools.ustr(per) +"""</para></td>
                                    <td><para style="answer">""" + tools.ustr(total) + """</para></td>
                                    <td><para style="answer_right">""" + tools.ustr(len(tot_res)) + """</para></td></tr>"""
                        rml+="""</blockTable>"""

                    rml +="""<blockTable colWidths="300,100,100.0" style="Table3">
                        <tr>
                              <td><para style="Standard1"></para></td>
                              <td><para style="Standard1">Answered Question</para></td>
                              <td><para style="Standard1">""" + tools.ustr(que.tot_resp) + """</para></td>
                        </tr>
                        <tr>
                            <td><para style="Standard1"></para></td>
                            <td><para style="Standard1">Skipped Question</para></td>
                            <td><para style="Standard1">""" + tools.ustr(survey.tot_start_survey - que.tot_resp) + """</para></td>
                        </tr>
                        </blockTable>"""
            rml += """</story>"""

        rml += """</document>"""
        report_type = datas.get('report_type', 'pdf')
        create_doc = self.generators[report_type]
        self.internal_header=True
        pdf = create_doc(rml, title=self.title)

        return (pdf, report_type)

survey_analysis('report.survey.analysis', 'survey','','')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
