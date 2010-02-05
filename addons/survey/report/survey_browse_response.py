# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import pooler
from report.interface import report_rml
from tools import to_xml
import tools
import time

class survey_browse_response(report_rml):
    def create(self, cr, uid, ids, datas, context):
        rml ="""<document filename="Survey Analysis Report.pdf">
                <template pageSize="(595.0,842.0)" title="Test" author="Martin Simon" allowSplitting="20">
                    <pageTemplate id="first">
                      <frame id="first" x1="57.0" y1="57.0" width="481" height="728"/>
                </pageTemplate>
                  </template>
                  <stylesheet>
                    <blockTableStyle id="ans_tbl_white">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                    </blockTableStyle>
                    <blockTableStyle id="ans_tbl_gainsboro">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <blockBackground colorName="gainsboro" start="0,0" stop="-1,-1"/>
                    </blockTableStyle>
                    <blockTableStyle id="Table1">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6"/>
                    </blockTableStyle>
                    <blockTableStyle id="note_table">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
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
                    <blockTableStyle id="Table41">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#000000" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEBEFORE" colorName="#777777" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEAFTER" colorName="#777777" start="0,0" stop="-1,-1"/>
                    </blockTableStyle>
                    <blockTableStyle id="Table51">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEBEFORE" colorName="#777777" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEAFTER" colorName="#777777" start="0,0" stop="-1,-1"/>
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
                    <paraStyle name="page" fontName="helvetica" fontSize="11.0" leftIndent="0.0"/>
                    <paraStyle name="question" fontName="helvetica-boldoblique" fontSize="10.0" leftIndent="3.0"/>
                    <paraStyle name="answer_bold" fontName="Helvetica-Bold" fontSize="09.0" leftIndent="2.0"/>
                    <paraStyle name="answer" fontName="helvetica" fontSize="09.0" leftIndent="2.0"/>
                    <paraStyle name="answer1" fontName="helvetica" fontSize="09.0" leftIndent="2.0"/>
                    <paraStyle name="Title" fontName="helvetica" fontSize="20.0" leading="15" spaceBefore="6.0" spaceAfter="6.0" alignment="CENTER"/>
                    <paraStyle name="P2" fontName="Helvetica" fontSize="14.0" leading="15" spaceBefore="6.0" spaceAfter="6.0"/>
                    <paraStyle name="comment" fontName="Helvetica" fontSize="14.0" leading="50" spaceBefore="0.0" spaceAfter="0.0"/>
                    <paraStyle name="P1" fontName="Helvetica" fontSize="9.0" leading="12" spaceBefore="0.0" spaceAfter="1.0"/>
                    <paraStyle name="terp_tblheader_Details" fontName="Helvetica-Bold" fontSize="9.0" leading="11" alignment="LEFT" spaceBefore="6.0" spaceAfter="6.0"/>
                    <paraStyle name="terp_default_9" fontName="Helvetica" fontSize="9.0" leading="11" alignment="LEFT" spaceBefore="0.0" spaceAfter="0.0"/>
                    <paraStyle name="terp_tblheader_General_Centre" fontName="Helvetica-Bold" fontSize="9.0" leading="10" alignment="CENTER" spaceBefore="6.0" spaceAfter="6.0"/>
                    <paraStyle name="terp_default_Centre_8" fontName="Helvetica" fontSize="9.0" leading="10" alignment="CENTER" spaceBefore="0.0" spaceAfter="0.0"/>
                  </stylesheet>
                  <images/>
                  <story>
                    <para style="Title"><u>Browse Responses </u></para>
                    <para style="Standard"><font></font></para>
                    <para style="P2">
                      <font color="white"> </font>
                    </para>
                    """
        surv_resp_obj = pooler.get_pool(cr.dbname).get('survey.response')
        if datas.has_key('form') and datas['form'].has_key('response_ids'):
            response_id = datas['form']['response_ids'][0][2]
        elif context.has_key('response_id'):
            response_id = [int(context['response_id'])]
        else:
            response_id = surv_resp_obj.search(cr, uid, [('survey_id','in',ids)])
        surv_resp_line_obj = pooler.get_pool(cr.dbname).get('survey.response.line')
        surv_obj = pooler.get_pool(cr.dbname).get('survey')
        surv_ans_obj = pooler.get_pool(cr.dbname).get('survey.answer')
        for response in surv_resp_obj.browse(cr,uid, response_id):
            for survey in surv_obj.browse(cr, uid, [response.survey_id.id]):
                status = "Not Finished"
                if response.state == "done":
                    status = "Finished"
                rml += """<blockTable colWidths="210.0,120.0,100.0,70" style="Table_heading">
                          <tr>
                            <td>
                              <para style="terp_tblheader_General_Centre">Survey Title </para>
                            </td>
                            <td>
                              <para style="terp_tblheader_General_Centre">Response Create Date </para>
                            </td>
                            <td>
                              <para style="terp_tblheader_General_Centre">Respose By </para>
                            </td>
                            <td>
                              <para style="terp_tblheader_General_Centre">Status</para>
                            </td>
                          </tr>
                          </blockTable>
                          <blockTable colWidths="210.0,120.0,100.0,70" style="Table_head_2">
                          <tr>
                            <td>
                              <para style="terp_default_Centre_8">""" + to_xml(tools.ustr(survey.title)) + """</para>
                            </td>
                            <td>
                              <para style="terp_default_Centre_8">""" + to_xml(time.strftime('%d-%m-%Y %I:%M:%S %p', time.strptime(response.date_create.split('.')[0], '%Y-%m-%d %H:%M:%S'))) + """</para>
                            </td>
                            <td>
                              <para style="terp_default_Centre_8">""" + to_xml(response.user_id.name) + """</para>
                            </td>
                            <td>
                              <para style="terp_default_Centre_8">""" + status + """</para>
                            </td>
                          </tr>
                        </blockTable>"""
                for page in survey.page_ids:
                    rml += """<para style="P2"></para>
                             <blockTable colWidths="500" style="Table4">
                                  <tr>
                                    <td><para style="page">Page :- """ + to_xml(tools.ustr(page.title)) + """</para></td>
                                  </tr>
                               </blockTable>"""
                    if page.note:
                        rml += """<para style="P2"></para>
                             <blockTable colWidths="500" style="note_table">
                                  <tr>
                                    <td><para style="response">""" + to_xml(tools.ustr(page.note)) + """</para></td>
                                  </tr>
                               </blockTable>"""
                    for que in page.question_ids:
                        rml += """<para style="P2"></para>
                                <blockTable colWidths="500" style="Table5">
                                  <tr>
                                    <td><para style="question">Que : """ + to_xml(to_xml(que.question)) + """</para></td>
                                  </tr>
                                 </blockTable>"""
                        answer = surv_resp_line_obj.browse(cr,uid, surv_resp_line_obj.search(cr, uid, [('question_id','=',que.id),('response_id','=',response.id)]))
                        if que.type in ['descriptive_text']:
                            rml +="""<blockTable colWidths="500" style="Table1">
                             <tr>  <td> <para style="response">""" + to_xml(tools.ustr(que.descriptive_text)) + """</para></td> </tr>
                            </blockTable>"""
                        elif que.type in ['table']:
                            if len(answer) and answer[0].state == "done":
                                col_heading = pooler.get_pool(cr.dbname).get('survey.tbl.column.heading')
                                cols_widhts = []
                                for col in range(0, len(que.column_heading_ids)):
                                    cols_widhts.append(float(500 / (len(que.column_heading_ids))))
                                colWidths = ",".join(map(tools.ustr, cols_widhts))
                                matrix_ans = []
                                rml +="""<para style="P2"></para><blockTable colWidths=" """ + str(colWidths) + """ " style="Table41"><tr>"""
                                for col in que.column_heading_ids:
                                    if col.title not in matrix_ans:
                                        matrix_ans.append(col.title)
                                        rml +="""<td> <para style="terp_tblheader_Details">""" + to_xml(tools.ustr(col.title)) +"""</para></td>"""
                                rml += """</tr></blockTable>"""
                                for row in range(0, que.no_of_rows):
                                    rml +="""<blockTable colWidths=" """ + str(colWidths) + """ " style="Table51"><tr>"""
                                    table_data = col_heading.browse(cr, uid, col_heading.search(cr, uid, [('response_table_id', '=', answer[0].id),('name','=',row)]))
                                    for column in matrix_ans:
                                        value = False
                                        for col in table_data:
                                            if column == col.column_id.title:
                                                value = col.value
                                        if value:
                                            rml += """<td> <para style="terp_default_9">""" + to_xml(tools.ustr(value)) +"""</para></td>"""
                                        else:
                                            rml += """<td><para style="terp_default_9"><font color ="white"> </font></para></td>"""
                                    rml += """</tr></blockTable>"""
                            else:
                                rml +="""<blockTable colWidths="500" style="Table1">
                                 <tr>  <td> <para style="response">No Response</para></td> </tr>
                                </blockTable>"""
                        elif que.type in ['multiple_choice_only_one_ans','multiple_choice_multiple_ans']:
                            if len(answer) and answer[0].state == "done":
                                ans_list = []
                                for ans in answer[0].response_answer_ids:
                                    ans_list.append(to_xml(tools.ustr(ans.answer_id.answer)))
                        
                                answer_choice=[]
                                _divide_columns_for_matrix = 20
                                _display_ans_in_rows = 5
                                _tbl_widths = 500
                                for ans in que['answer_choice_ids']:
                                    answer_choice.append(to_xml(tools.ustr((ans.answer))))
        
                                def divide_list(lst, n):
                                    return [lst[i::n] for i in range(n)]
        
                                divide_list = divide_list(answer_choice,_display_ans_in_rows)
                                for lst in divide_list:
                                    if que.type == 'multiple_choice_multiple_ans':
                                        if len(lst)<>0 and len(lst)<>int(round(float(len(answer_choice))/_display_ans_in_rows,0)):
                                           lst.append('')
                                    if not lst:
                                       del divide_list[divide_list.index(lst):]
                                for divide in divide_list:
                                    a = _divide_columns_for_matrix*len(divide)
                                    b = float(_tbl_widths) - float(a)
                                    cols_widhts=[]
                                    for div in range(0,len(divide)):
                                        cols_widhts.append(float(a/len(divide)))
                                        cols_widhts.append(float(b/len(divide)))
                                    colWidths = ",".join(map(tools.ustr, cols_widhts))
                                    rml+="""<blockTable colWidths=" """ + colWidths + """ " style="Table1">
                                                <tr>"""
                                    for div in range(0,len(divide)):
                                       if divide[div]!='':
                                           if que.type == 'multiple_choice_multiple_ans':
                                               if divide[div] in ans_list:
                                                   rml += """<td><illustration><fill color="white"/>
                                                        <rect x="0.1cm" y="-0.45cm" width="0.5 cm" height="0.5cm" fill="yes" stroke="yes"  round="0.1cm"/>
                                                        <fill color="gray"/>
                                                        <rect x="0.2cm" y="-0.35cm" width="0.3 cm" height="0.3cm" fill="yes" stroke="no"  round="0.1cm"/>
                                                        </illustration></td>
                                                   <td><para style="answer">""" + divide[div] + """</para></td>"""
                                               else:
                                                   rml+="""
                                                   <td>
                                                       <illustration>
                                                           <rect x="0.1cm" y="-0.45cm" width="0.5 cm" height="0.5cm" fill="no" stroke="yes"  round="0.1cm"/>
                                                        </illustration>
                                                   </td>
                                                   <td><para style="answer">""" + divide[div] + """</para></td>"""
                                           else:
                                               if divide[div] in ans_list:
                                                   rml += """<td><illustration><fill color="white"/>
                                                            <circle x="0.3cm" y="-0.18cm" radius="0.22 cm" fill="yes" stroke="yes" round="0.1cm"/>
                                                            <fill color="gray"/>
                                                            <circle x="0.3cm" y="-0.18cm" radius="0.10 cm" fill="yes" stroke="no" round="0.1cm"/>
                                                        </illustration></td>
                                                   <td><para style="answer">""" + divide[div] + """</para></td>"""
                                               else:
                                                   rml+="""
                                               <td>
                                                   <illustration>
                                                       <circle x="0.3cm" y="-0.18cm" radius="0.23 cm" fill="no" stroke="yes" round="0.1cm"/>
                                                    </illustration>
                                               </td>
                                               <td><para style="answer">""" + divide[div] + """</para></td>"""
                                       else:
                                           rml+="""
                                           <td></td>
                                           <td></td>"""
                                    rml+="""</tr></blockTable>"""
                                if que.is_comment_require and answer[0].comment:
                                    rml+="""<blockTable colWidths="500" style="Table1"><tr>
                                                <td><para style="answer">""" + to_xml(tools.ustr(answer[0].comment)) + """</para></td></tr></blockTable>"""

                            else:
                                rml +="""<blockTable colWidths="500" style="Table1">
                                 <tr>  <td> <para style="response">No Response</para></td> </tr>
                                </blockTable>"""
                        elif que.type in ['multiple_textboxes_diff_type','multiple_textboxes','date','date_and_time','numerical_textboxes','multiple_textboxes_diff_type']:
                            if len(answer) and answer[0].state == "done":
                                answer_list = {}
                                for ans in answer[0].response_answer_ids:
                                    answer_list[ans.answer_id.answer] = ans.answer
                                for que_ans in que['answer_choice_ids']:
                                    if que_ans.answer in answer_list:
                                        rml +="""<blockTable colWidths="200,300" style="Table1">
                                             <tr> <td> <para style="response">""" + to_xml(tools.ustr(que_ans.answer)) + """</para></td>
                                             <td> <para style="response">""" + to_xml(tools.ustr(answer_list[que_ans.answer])) + """</para></td></tr>
                                            </blockTable>"""
                                    else:
                                        rml +="""<blockTable colWidths="200,300" style="Table1">
                                             <tr> <td> <para style="response">""" + to_xml(tools.ustr(que_ans.answer)) + """</para></td>
                                             <td> <para style="response"></para></td></tr>
                                            </blockTable>"""
                            else:
                                rml +="""<blockTable colWidths="500" style="Table1">
                                 <tr>  <td> <para style="response">No Response</para></td> </tr>
                                </blockTable>"""
                        elif que.type in ['single_textbox']:
                            if len(answer) and answer[0].state == "done":
                                rml +="""<blockTable colWidths="500" style="Table1">
                                     <tr> <td> <para style="response">""" + to_xml(tools.ustr(answer[0].single_text)) + """</para></td></tr>
                                    </blockTable>"""
                            else:
                                rml +="""<blockTable colWidths="500" style="Table1">
                                 <tr>  <td> <para style="response">No Response</para></td> </tr>
                                </blockTable>"""
                        elif que.type in ['comment']:
                            if len(answer) and answer[0].state == "done":
                                rml +="""<blockTable colWidths="500" style="Table1">
                                     <tr> <td> <para style="response">""" + to_xml(tools.ustr(answer[0].comment)) + """</para></td></tr>
                                    </blockTable>"""
                            else:
                                rml +="""<blockTable colWidths="500" style="Table1">
                                 <tr>  <td> <para style="response">No Response</para></td> </tr>
                                </blockTable>"""
                        elif que.type in ['matrix_of_choices_only_one_ans','matrix_of_choices_only_multi_ans','rating_scale','matrix_of_drop_down_menus']:
                            if len(answer) and answer[0].state == "done":
                                if que.type  in ['matrix_of_choices_only_one_ans','rating_scale'] and que.comment_column:
                                    pass
                                cols_widhts = []
                                cols_widhts.append(200)
                                len_col_heading = len(que.column_heading_ids)
                                for col in range(0, len_col_heading):
                                    cols_widhts.append(float(300 / len_col_heading))
                                tmp=0.0
                                sum = 0.0
                                i = 0
                                if que.type in ['matrix_of_choices_only_one_ans','rating_scale'] and que.comment_column:
                                    for col in cols_widhts:
                                        if i==0:
                                            cols_widhts[i] = cols_widhts[i]/2.0
                                            tmp = cols_widhts[i]
                                        sum += col
                                        i+=1
                                    cols_widhts.append(round(tmp,2))
                                colWidths = ",".join(map(tools.ustr, cols_widhts))
                                matrix_ans = [(0,''),]
                                for col in que.column_heading_ids:
                                    if col.title not in matrix_ans:
                                        matrix_ans.append((col.id,col.title))
                                len_matrix = len(matrix_ans)
                                if que.type in ['matrix_of_choices_only_one_ans','rating_scale'] and que.comment_column:
                                    matrix_ans.append(que.column_name)
                                rml+="""<blockTable colWidths=" """ + colWidths + """ " style="Table1"><tr>"""
                                for mat_col in range(0, len(matrix_ans)):
                                    rml+="""<td><para style="response">""" + to_xml(tools.ustr(matrix_ans[mat_col][1])) + """</para></td>"""
                                rml +="""</tr>"""
                                rml+="""</blockTable>"""
                                i=0
                                for ans in que.answer_choice_ids:
                                    if i%2!=0:
                                        style='ans_tbl_white'
                                    else:
                                        style='ans_tbl_gainsboro'
                                    i+=1
                                    rml+="""<blockTable colWidths=" """ + colWidths + """ " style='"""+style+"""'>
                                    <tr><td><para style="response">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>"""
                                    comment_value = ""
                                    for mat_col in range(1, len_matrix):
                                        value = """"""
                                        for res_ans in answer[0].response_answer_ids:
                                            if res_ans.answer_id.id == ans.id and res_ans.column_id.id == matrix_ans[mat_col][0]:
                                                comment_value =  to_xml(tools.ustr(res_ans.comment_field))
                                                if que.type in ['matrix_of_drop_down_menus']:
                                                    value = """<para style="response">""" + to_xml(tools.ustr(res_ans.value_choice)) + """</para>"""
                                                elif que.type in ['matrix_of_choices_only_one_ans','rating_scale']:
                                                    value = """<illustration><fill color="white"/>
                                                            <circle x="0.3cm" y="-0.18cm" radius="0.22 cm" fill="yes" stroke="yes"/>
                                                            <fill color="gray"/>
                                                            <circle x="0.3cm" y="-0.18cm" radius="0.10 cm" fill="yes" stroke="no"/>
                                                        </illustration>"""
                                                elif que.type in ['matrix_of_choices_only_multi_ans']:
                                                    value = """<illustration>
                                                        <fill color="white"/>
                                                        <rect x="0.1cm" y="-0.45cm" width="0.5 cm" height="0.5cm" fill="yes" stroke="yes"  round="0.1cm"/>
                                                        <fill color="gray"/>
                                                        <rect x="0.2cm" y="-0.35cm" width="0.3 cm" height="0.3cm" fill="yes" stroke="no"  round="0.1cm"/>
                                                        </illustration>"""
                                                break
                                            else:
                                                if que.type in ['matrix_of_drop_down_menus']:
                                                    value = """"""
                                                elif que.type in ['matrix_of_choices_only_one_ans','rating_scale']:
                                                    value = """<illustration><fill color="white"/>
                                                            <circle x="0.3cm" y="-0.18cm" radius="0.22 cm" fill="yes" stroke="yes"  round="0.1cm"/>
                                                        </illustration>"""
                                                elif que.type in ['matrix_of_choices_only_multi_ans']:
                                                    value = """<illustration><fill color="white"/>
                                                        <rect x="0.1cm" y="-0.45cm" width="0.5 cm" height="0.5cm" fill="yes" stroke="yes"  round="0.1cm"/>
                                                        </illustration>"""
                                        rml+= """<td>""" + value + """</td>"""
                                    if que.type in ['matrix_of_choices_only_one_ans','rating_scale'] and que.comment_column:
                                        if comment_value=='False':
                                            comment_value = ''
                                        rml+= """<td><para style="response">"""+ to_xml(tools.ustr(comment_value)) + """</para></td>"""
                                    rml+="""  </tr></blockTable>"""
                                if que.is_comment_require:
                                    rml+="""<blockTable colWidths="500" style="Table1"><tr>
                                            <td><para style="answer">""" + to_xml(tools.ustr(answer[0].comment or '')) + """</para></td></tr></blockTable>"""
                            else:
                                rml +="""<blockTable colWidths="500" style="Table1">
                                 <tr>  <td> <para style="response">No Response</para></td> </tr>
                                </blockTable>"""

                    rml += """<pageBreak/>"""
        rml += """</story></document>"""
        report_type = datas.get('report_type', 'pdf')
        create_doc = self.generators[report_type]
        pdf = create_doc(rml, title=self.title)
        return (pdf, report_type)

survey_browse_response('report.survey.browse.response', 'survey','','')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

