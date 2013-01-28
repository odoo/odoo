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

class survey_browse_response(report_rml):
    def create(self, cr, uid, ids, datas, context):
        _divide_columns_for_matrix = 0.7
        _display_ans_in_rows = 5
        _pageSize = ('29.7cm','21.1cm')

        if datas.has_key('form') and datas['form'].get('orientation','') == 'vertical':
            if datas['form'].get('paper_size','') == 'letter':
                _pageSize = ('21.6cm','27.9cm')
            elif datas['form'].get('paper_size','') == 'legal':
                _pageSize = ('21.6cm','35.6cm')
            elif datas['form'].get('paper_size','') == 'a4':
                _pageSize = ('21.1cm','29.7cm')

        elif datas.has_key('form') and datas['form'].get('orientation',False) == 'horizontal':
            if datas['form'].get('paper_size','') == 'letter':
                _pageSize = ('27.9cm','21.6cm')
            elif datas['form'].get('paper_size','') == 'legal':
                _pageSize = ('35.6cm','21.6cm')
            elif datas['form'].get('paper_size') == 'a4':
                _pageSize = ('29.7cm','21.1cm')

        _frame_width = tools.ustr(_pageSize[0])
        _frame_height = tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.90))+'cm'
        _tbl_widths = tools.ustr(float(_pageSize[0].replace('cm','')) - float(2.10))+'cm'
        rml ="""<document filename="Survey Answer Report.pdf">
                <template pageSize="("""+_pageSize[0]+""","""+_pageSize[1]+""")" title='Survey Answer' author="OpenERP S.A.(sales@openerp.com)" allowSplitting="20" >
                    <pageTemplate id="first">
                        <frame id="first" x1="0.0cm" y1="1.0cm" width='"""+_frame_width+"""' height='"""+_frame_height+"""'/>
                        <pageGraphics>
                            <lineMode width="1.0"/>
                            <lines>1.0cm """+tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.00))+'cm'+""" """+tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00))+'cm'+""" """+tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.00))+'cm'+"""</lines>
                            <lines>1.0cm """+tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.00))+'cm'+""" 1.0cm 1.00cm</lines>
                            <lines>"""+tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00))+'cm'+""" """+tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.00))+'cm'+""" """+tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00))+'cm'+""" 1.00cm</lines>
                            <lines>1.0cm 1.00cm """+tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00))+'cm'+""" 1.00cm</lines>"""
        if datas.has_key('form') and datas['form']['page_number']:
            rml +="""
                    <fill color="gray"/>
                    <setFont name="Helvetica" size="10"/>
                    <drawRightString x='"""+tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00))+'cm'+"""' y="0.6cm">Page : <pageNumber/> </drawRightString>"""
        rml +="""</pageGraphics>
                    </pageTemplate>
                </template>
                  <stylesheet>
                    <blockTableStyle id="tbl_white">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEBEFORE" colorName="#777777" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEAFTER" colorName="#777777" start="0,0" stop="-1,-1"/>
                    </blockTableStyle>
                    <blockTableStyle id="tbl_gainsboro">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEBEFORE" colorName="#777777" start="0,0" stop="-1,-1"/>
                      <lineStyle kind="LINEAFTER" colorName="#777777" start="0,0" stop="-1,-1"/>
                      <blockBackground colorName="gainsboro" start="0,0" stop="-1,-1"/>
                    </blockTableStyle>
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
                    <blockTableStyle id="simple_table">
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
                    </blockTableStyle>
                    <blockTableStyle id="title_tbl">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#000000" start="0,-1" stop="1,-1"/>
                      <blockBackground colorName="black" start="0,0" stop="-1,-1"/>
                      <blockTextColor colorName="white" start="0,0" stop="0,0"/>
                    </blockTableStyle>
                    <blockTableStyle id="page_tbl">
                      <blockAlignment value="LEFT"/>
                      <blockValign value="TOP"/>
                      <lineStyle kind="LINEBELOW" colorName="#000000" start="0,-1" stop="1,-1"/>
                      <blockBackground colorName="gray" start="0,0" stop="-1,-1"/>
                      <blockTextColor colorName="white" start="0,0" stop="0,0"/>
                    </blockTableStyle>
                    <initialize>
                      <paraStyle name="all" alignment="justify"/>
                    </initialize>
                    <paraStyle name="title" fontName="helvetica-bold" fontSize="18.0" leftIndent="0.0" textColor="white"/>
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
                    <paraStyle name="terp_default_9_Bold" fontName="Helvetica-Bold" fontSize="9.0" leading="11" alignment="LEFT" spaceBefore="0.0" spaceAfter="0.0"/>
                    <paraStyle name="terp_tblheader_General_Centre_simple" fontName="Helvetica" fontSize="10.0" leading="10" alignment="LEFT" spaceBefore="6.0" spaceAfter="6.0"/>
                    <paraStyle name="terp_tblheader_General_Centre" fontName="Helvetica-Bold" fontSize="10.0" leading="10" alignment="LEFT" spaceBefore="6.0" spaceAfter="6.0"/>
                    <paraStyle name="terp_tblheader_General_right_simple" fontName="Helvetica" fontSize="10.0" leading="10" alignment="RIGHT" spaceBefore="6.0" spaceAfter="6.0"/>
                    <paraStyle name="terp_tblheader_General_right" fontName="Helvetica-Bold" fontSize="10.0" leading="10" alignment="RIGHT" spaceBefore="6.0" spaceAfter="6.0"/>
                    <paraStyle name="descriptive_text" fontName="helvetica-bold" fontSize="18.0" leftIndent="0.0" textColor="white"/>
                    <paraStyle name="descriptive_text_heading" fontName="helvetica-bold" fontSize="18.0" alignment="RIGHT" leftIndent="0.0" textColor="white"/>
                  </stylesheet>
                  <images/>
                  <story>"""
        surv_resp_obj = pooler.get_pool(cr.dbname).get('survey.response')
        rml_obj=report_sxw.rml_parse(cr, uid, surv_resp_obj._name,context)
        if datas.has_key('form') and datas['form'].has_key('response_ids'):
            response_id = datas['form']['response_ids']
        elif context.has_key('response_id') and context['response_id']:
            response_id = [int(context['response_id'][0])]
        else:
            response_id = surv_resp_obj.search(cr, uid, [('survey_id', 'in', ids)])

        surv_resp_line_obj = pooler.get_pool(cr.dbname).get('survey.response.line')
        surv_obj = pooler.get_pool(cr.dbname).get('survey')

        for response in surv_resp_obj.browse(cr, uid, response_id):
            for survey in surv_obj.browse(cr, uid, [response.survey_id.id]):
                tbl_width = float(_tbl_widths.replace('cm', ''))
                colwidth =  "2.5cm,4.8cm," + str(tbl_width - 15.0) +"cm,3.2cm,4.5cm"
                resp_create = tools.ustr(time.strftime('%d-%m-%Y %I:%M:%S %p', time.strptime(response.date_create.split('.')[0], '%Y-%m-%d %H:%M:%S')))
                rml += """<blockTable colWidths='""" + colwidth + """' style="Table_heading">
                          <tr>
                            <td><para style="terp_default_9_Bold">Print Date : </para></td>
                            <td><para style="terp_default_9">""" + to_xml(rml_obj.formatLang(time.strftime("%Y-%m-%d %H:%M:%S"),date_time=True)) + """</para></td>
                            <td><para style="terp_default_9"></para></td>
                            <td><para style="terp_default_9_Bold">Answered by : </para></td>
                            <td><para style="terp_default_9">""" + to_xml(response.user_id.login or '') + """</para></td>
                          </tr>
                          <tr>
                            <td><para style="terp_default_9"></para></td>
                            <td><para style="terp_default_9"></para></td>
                            <td><para style="terp_default_9"></para></td>
                            <td><para style="terp_default_9_Bold">Answer Date : </para></td>
                            <td><para style="terp_default_9">""" + to_xml(resp_create) +  """</para></td>
                          </tr>
                        </blockTable><para style="P2"></para>"""

                status = "Not Finished"
                if response.state == "done": status = "Finished"
                colwidth =  str(tbl_width - 7) + "cm,"
                colwidth +=  "7cm"
                rml += """<blockTable colWidths='""" + str(colwidth) + """' style="title_tbl">
                            <tr>
                            <td><para style="title">""" + to_xml(tools.ustr(survey.title)) + """</para><para style="P2"><font></font></para></td>
                            <td><para style="descriptive_text_heading">Status :- """ + to_xml(tools.ustr(status)) + """</para><para style="P2"><font></font></para></td>
                            </tr>
                        </blockTable>"""

                if survey.note:
                    rml += """<blockTable colWidths='""" + _tbl_widths + """' style="note_table">
                            <tr><td><para style="response">""" + to_xml(tools.ustr(survey.note or '')) + """</para><para style="P2"><font></font></para></td></tr>
                        </blockTable>"""

                for page in survey.page_ids:
                    rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="page_tbl">
                                  <tr><td><para style="page">Page :- """ + to_xml(tools.ustr(page.title or '')) + """</para></td></tr>
                              </blockTable>"""
                    if page.note:
                        rml += """<para style="P2"></para>
                                 <blockTable colWidths='""" + str(_tbl_widths) + """' style="note_table">
                                      <tr><td><para style="response">""" + to_xml(tools.ustr(page.note or '')) + """</para></td></tr>
                                 </blockTable>"""

                    for que in page.question_ids:
                        rml += """<para style="P2"></para>
                                <blockTable colWidths='""" + str(_tbl_widths) + """' style="Table5">
                                  <tr><td><para style="question">""" + to_xml(to_xml(que.question)) + """</para></td></tr>
                                </blockTable>"""

                        answer = surv_resp_line_obj.browse(cr ,uid, surv_resp_line_obj.search(cr, uid, [('question_id', '=', que.id),('response_id', '=', response.id)]))
                        if que.type in ['descriptive_text']:
                            rml +="""<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                         <tr><td> <para style="response">""" + to_xml(tools.ustr(que.descriptive_text)) + """</para></td> </tr>
                                    </blockTable>"""

                        elif que.type in ['table']:
                            if len(answer) and answer[0].state == "done":
                                col_heading = pooler.get_pool(cr.dbname).get('survey.tbl.column.heading')
                                cols_widhts = []
                                tbl_width = float(_tbl_widths.replace('cm', ''))
                                for i in range(0, len(que.column_heading_ids)):
                                    cols_widhts.append(tbl_width / float(len(que.column_heading_ids)))
                                colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                                colWidths = colWidths + 'cm'
                                matrix_ans = []
                                rml +="""<para style="P2"></para><blockTable colWidths=" """ + str(colWidths) + """ " style="Table41"><tr>"""

                                for col in que.column_heading_ids:
                                    if col.title not in matrix_ans:
                                        matrix_ans.append(col.title)
                                        rml += """<td> <para style="terp_tblheader_Details">""" + to_xml(tools.ustr(col.title)) +"""</para></td>"""
                                rml += """</tr></blockTable>"""
                                i = 0

                                for row in range(0, que.no_of_rows):
                                    if i%2 != 0:
                                        style = 'tbl_white'
                                    else:
                                        style = 'tbl_gainsboro'
                                    i +=1
                                    rml += """<blockTable colWidths=" """ + str(colWidths) + """ " style='"""+style+"""'><tr>"""
                                    table_data = col_heading.browse(cr, uid, col_heading.search(cr, uid, [('response_table_id', '=', answer[0].id), ('name', '=', row)]))
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
                                rml +="""<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                             <tr><td> <para style="response">No Answer</para></td> </tr>
                                        </blockTable>"""

                        elif que.type in ['multiple_choice_only_one_ans','multiple_choice_multiple_ans']:
                            if len(answer) and answer[0].state == "done":
                                ans_list = []
                                for ans in answer[0].response_answer_ids:
                                    ans_list.append(to_xml(tools.ustr(ans.answer_id.answer)))
                                answer_choice=[]

                                for ans in que['answer_choice_ids']:
                                    answer_choice.append(to_xml(tools.ustr((ans.answer))))

                                def divide_list(lst, n):
                                    return [lst[i::n] for i in range(n)]

                                divide_list = divide_list(answer_choice,_display_ans_in_rows)
                                for lst in divide_list:
                                    if que.type == 'multiple_choice_multiple_ans':
                                        if len(lst) <> 0 and len(lst) <> int(round(float(len(answer_choice)) / _display_ans_in_rows, 0)):
                                           lst.append('')
                                    if not lst:
                                       del divide_list[divide_list.index(lst):]

                                for divide in divide_list:
                                    a = _divide_columns_for_matrix * len(divide)
                                    b = float(_tbl_widths.replace('cm', '')) - float(a)
                                    cols_widhts = []
                                    for div in range(0, len(divide)):
                                        cols_widhts.append(float(a / len(divide)))
                                        cols_widhts.append(float(b / len(divide)))
                                    colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                                    colWidths = colWidths +'cm'
                                    rml += """<blockTable colWidths=" """ + colWidths + """ " style="simple_table"><tr>"""

                                    for div in range(0, len(divide)):
                                       if divide[div] != '':
                                           if que.type == 'multiple_choice_multiple_ans':
                                               if divide[div] in ans_list:
                                                   rml += """<td><illustration><fill color="white"/>
                                                                <rect x="0.1cm" y="-0.45cm" width="0.5 cm" height="0.5cm" fill="yes" stroke="yes"  round="0.1cm"/>
                                                                <fill color="gray"/>
                                                                <rect x="0.2cm" y="-0.35cm" width="0.3 cm" height="0.3cm" fill="yes" stroke="no"  round="0.1cm"/>
                                                                </illustration></td>
                                                             <td><para style="answer">""" + divide[div] + """</para></td>"""
                                               else:
                                                   rml+="""<td><illustration>
                                                           <rect x="0.1cm" y="-0.45cm" width="0.5 cm" height="0.5cm" fill="no" stroke="yes"  round="0.1cm"/>
                                                            </illustration></td>
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
                                                   rml += """<td>
                                                               <illustration>
                                                                   <circle x="0.3cm" y="-0.18cm" radius="0.23 cm" fill="no" stroke="yes" round="0.1cm"/>
                                                                </illustration>
                                                           </td>
                                                           <td><para style="answer">""" + divide[div] + """</para></td>"""
                                       else:
                                           rml += """<td></td><td></td>"""
                                    rml += """</tr></blockTable>"""

                                if que.is_comment_require and answer[0].comment:
                                    rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table"><tr>
                                                <td><para style="answer">""" + to_xml(tools.ustr(answer[0].comment)) + """</para></td></tr></blockTable>"""
                            else:
                                rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                             <tr><td> <para style="response">No Answer</para></td> </tr>
                                          </blockTable>"""

                        elif que.type in ['multiple_textboxes_diff_type','multiple_textboxes','date','date_and_time','numerical_textboxes','multiple_textboxes_diff_type']:
                            if len(answer) and answer[0].state == "done":
                                cols_widhts = []
                                cols_widhts.append(float(_tbl_widths.replace('cm',''))/2)
                                cols_widhts.append(float(_tbl_widths.replace('cm',''))/2)
                                colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                                colWidths = tools.ustr(colWidths) + 'cm'
                                answer_list = {}

                                for ans in answer[0].response_answer_ids:
                                    answer_list[ans.answer_id.answer] = ans.answer
                                for que_ans in que['answer_choice_ids']:
                                    if que_ans.answer in answer_list:
                                        rml += """<blockTable colWidths='""" + str(colWidths) + """' style="simple_table">
                                                 <tr> <td> <para style="response">""" + to_xml(tools.ustr(que_ans.answer)) + """</para></td>
                                                 <td> <para style="response">""" + to_xml(tools.ustr(answer_list[que_ans.answer])) + """</para></td></tr>
                                                </blockTable>"""
                                    else:
                                        rml += """<blockTable colWidths='""" + str(colWidths) + """' style="simple_table">
                                                 <tr> <td> <para style="response">""" + to_xml(tools.ustr(que_ans.answer)) + """</para></td>
                                                 <td> <para style="response"></para></td></tr>
                                                </blockTable>"""
                            else:
                                rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                         <tr>  <td> <para style="response">No Answer</para></td> </tr>
                                        </blockTable>"""

                        elif que.type in ['single_textbox']:
                            if len(answer) and answer[0].state == "done":
                                rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                         <tr> <td> <para style="response">""" + to_xml(tools.ustr(answer[0].single_text)) + """</para></td></tr>
                                        </blockTable>"""
                            else:
                                rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                         <tr>  <td> <para style="response">No Answer</para></td> </tr>
                                        </blockTable>"""

                        elif que.type in ['comment']:
                            if len(answer) and answer[0].state == "done":
                                rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                         <tr> <td> <para style="response">""" + to_xml(tools.ustr(answer[0].comment)) + """</para></td></tr>
                                        </blockTable>"""
                            else:
                                rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                         <tr>  <td> <para style="response">No Answer</para></td> </tr>
                                        </blockTable>"""

                        elif que.type in ['matrix_of_choices_only_one_ans','matrix_of_choices_only_multi_ans', 'rating_scale', 'matrix_of_drop_down_menus']:
                            if len(answer) and answer[0].state == "done":
                                if que.type  in ['matrix_of_choices_only_one_ans', 'rating_scale'] and que.comment_column:
                                    pass
                                cols_widhts = []
                                if len(que.column_heading_ids):
                                    cols_widhts.append(float(_tbl_widths.replace('cm','')) / float(2.0))
                                    for col in que.column_heading_ids:
                                        cols_widhts.append(float((float(_tbl_widths.replace('cm','')) / float(2.0)) / len(que.column_heading_ids)))
                                else:
                                    cols_widhts.append(float(_tbl_widths.replace('cm','')))

                                tmp = 0.0
                                sum =  0.0
                                i = 0
                                if que.type in ['matrix_of_choices_only_one_ans','rating_scale'] and que.comment_column:
                                    for col in cols_widhts:
                                        if i == 0:
                                            cols_widhts[i] = cols_widhts[i] / 2.0
                                            tmp = cols_widhts[i]
                                        sum += col
                                        i += 1
                                    cols_widhts.append(round(tmp, 2))
                                colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                                colWidths = colWidths + 'cm'
                                matrix_ans = [(0, ''),]

                                for col in que.column_heading_ids:
                                    if col.title not in matrix_ans:
                                        matrix_ans.append((col.id, col.title))
                                len_matrix = len(matrix_ans)
                                if que.type in ['matrix_of_choices_only_one_ans', 'rating_scale'] and que.comment_column:
                                    matrix_ans.append((0,que.column_name))
                                rml += """<blockTable colWidths=" """ + colWidths + """ " style="simple_table"><tr>"""

                                for mat_col in range(0, len(matrix_ans)):
                                    rml += """<td><para style="response">""" + to_xml(tools.ustr(matrix_ans[mat_col][1])) + """</para></td>"""
                                rml += """</tr>"""
                                rml += """</blockTable>"""
                                i = 0

                                for ans in que.answer_choice_ids:
                                    if i%2 != 0:
                                        style = 'ans_tbl_white'
                                    else:
                                        style = 'ans_tbl_gainsboro'
                                    i += 1
                                    rml += """<blockTable colWidths=" """ + colWidths + """ " style='"""+style+"""'>
                                            <tr><td><para style="response">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>"""
                                    comment_value = ""
                                    for mat_col in range(1, len_matrix):
                                        value = """"""
                                        for res_ans in answer[0].response_answer_ids:
                                            if res_ans.answer_id.id == ans.id and res_ans.column_id.id == matrix_ans[mat_col][0]:
                                                comment_value = to_xml(tools.ustr(res_ans.comment_field))
                                                if que.type in ['matrix_of_drop_down_menus']:
                                                    value = """<para style="response">""" + to_xml(tools.ustr(res_ans.value_choice)) + """</para>"""
                                                elif que.type in ['matrix_of_choices_only_one_ans', 'rating_scale']:
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
                                        if comment_value == 'False':
                                            comment_value = ''
                                        rml += """<td><para style="response">""" + to_xml(tools.ustr(comment_value)) + """</para></td>"""
                                    rml += """</tr></blockTable>"""

                                if que.is_comment_require:
                                    rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table"><tr>
                                            <td><para style="answer">""" + to_xml(tools.ustr(answer[0].comment or '')) + """</para></td></tr></blockTable>"""
                            else:
                                rml += """<blockTable colWidths='""" + str(_tbl_widths) + """' style="simple_table">
                                         <tr><td> <para style="response">No Answer</para></td> </tr>
                                        </blockTable>"""

                if datas.has_key('form') and not datas['form']['without_pagebreak']:
                    rml += """<pageBreak/>"""
                elif not datas.has_key('form'):
                    rml += """<pageBreak/>"""
                else:
                    rml += """<para style="P2"><font></font></para>"""

        rml += """</story></document>"""
        report_type = datas.get('report_type', 'pdf')
        create_doc = self.generators[report_type]
        pdf = create_doc(rml, title=self.title)
        return (pdf, report_type)

survey_browse_response('report.survey.browse.response', 'survey','','')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
