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

from openerp import pooler, tools
from openerp.report.interface import report_rml
from openerp.tools import to_xml

class survey_form(report_rml):
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
        elif datas.has_key('form') and datas['form'].get('orientation','') == 'horizontal':
            if datas['form'].get('paper_size','') == 'letter':
                _pageSize = ('27.9cm','21.6cm')
            elif datas['form'].get('paper_size','') == 'legal':
                _pageSize = ('35.6cm','21.6cm')
            elif datas['form'].get('paper_size','') == 'a4':
                _pageSize = ('29.7cm','21.1cm')

        _frame_width = tools.ustr(_pageSize[0])
        _frame_height = tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.90))+'cm'
        _tbl_widths = tools.ustr(float(_pageSize[0].replace('cm','')) - float(2.10))+'cm'

        rml="""<document filename="Survey Form.pdf">
            <template pageSize="("""+_pageSize[0]+""","""+_pageSize[1]+""")" title='Survey Form' author="OpenERP S.A.(sales@openerp.com)" allowSplitting="20" >
                <pageTemplate id="first">
                    <frame id="first" x1="0.0cm" y1="1.0cm" width='"""+_frame_width+"""' height='"""+_frame_height+"""'/>
                    <pageGraphics>
                        <lineMode width="1.0"/>
                        <lines>1.0cm """ + tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.00)) + 'cm' + """ """+tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00))+'cm'+""" """+tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.00)) + 'cm' + """</lines>
                        <lines>1.0cm """ + tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.00)) +'cm'+ """ 1.0cm 1.00cm</lines>
                        <lines>""" + tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00))+'cm' + """ """ + tools.ustr(float(_pageSize[1].replace('cm','')) - float(1.00))+'cm'+""" """+tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00)) + 'cm' + """ 1.00cm</lines>
                        <lines>1.0cm 1.00cm """ + tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00))+'cm'+""" 1.00cm</lines>"""

        if datas.has_key('form') and datas['form']['page_number']:
            rml +="""
                    <fill color="gray"/>
                    <setFont name="Helvetica" size="10"/>
                    <drawRightString x='""" + tools.ustr(float(_pageSize[0].replace('cm','')) - float(1.00)) + 'cm' + """' y="0.6cm">Page : <pageNumber/> </drawRightString>"""
        rml +="""</pageGraphics>
                </pageTemplate>
            </template>
            <stylesheet>
            <blockTableStyle id="ans_tbl">
              <blockAlignment value="LEFT"/>
              <blockValign value="TOP"/>
              <lineStyle kind="LINEBELOW" colorName="#e6e6e6" start="0,0" stop="-1,-1"/>
            </blockTableStyle>
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
            <blockTableStyle id="page_tbl">
              <blockAlignment value="LEFT"/>
              <blockValign value="TOP"/>
              <lineStyle kind="LINEBELOW" colorName="#000000" start="0,-1" stop="1,-1"/>
              <blockBackground colorName="gray" start="0,0" stop="-1,-1"/>
              <blockTextColor colorName="white" start="0,0" stop="0,0"/>
            </blockTableStyle>
            <blockTableStyle id="title_tbl">
              <blockAlignment value="LEFT"/>
              <blockValign value="TOP"/>
              <lineStyle kind="LINEBELOW" colorName="#000000" start="0,-1" stop="1,-1"/>
              <blockBackground colorName="black" start="0,0" stop="-1,-1"/>
              <blockTextColor colorName="white" start="0,0" stop="0,0"/>
            </blockTableStyle>
            <blockTableStyle id="question_tbl">
              <blockAlignment value="LEFT"/>
              <blockValign value="TOP"/>
              <lineStyle kind="LINEBELOW" colorName="#8f8f8f" start="0,-1" stop="1,-1"/>
            </blockTableStyle>
            <blockTableStyle id="note_table">
              <blockAlignment value="LEFT"/>
              <blockValign value="TOP"/>
            </blockTableStyle>
            <blockTableStyle id="tbl">
              <blockAlignment value="LEFT"/>
              <blockValign value="TOP"/>
              <lineStyle kind="LINEBELOW" colorName="#000000" start="0,0" stop="-1,-1"/>
              <lineStyle kind="LINEBEFORE" colorName="#777777" start="0,0" stop="-1,-1"/>
              <lineStyle kind="LINEAFTER" colorName="#777777" start="0,0" stop="-1,-1"/>
            </blockTableStyle>
            <initialize>
              <paraStyle name="all" alignment="justify"/>
            </initialize>
            <paraStyle name="response" fontName="Helvetica-oblique" fontSize="9.5"/>
            <paraStyle name="page" fontName="helvetica-bold" fontSize="15.0" leftIndent="0.0" textColor="white"/>
            <paraStyle name="title" fontName="helvetica-bold" fontSize="18.0" leading="15" leftIndent="0.0" textColor="white"/>
            <paraStyle name="question" fontName="helvetica-boldoblique" fontSize="10.0" leftIndent="3.0"/>
            <paraStyle name="answer" fontName="helvetica" fontSize="09.0" leftIndent="0.0"/>
            <paraStyle name="descriptive_text" fontName="helvetica" fontSize="10.0" leftIndent="0.0"/>
            <paraStyle name="answer_left" alignment="LEFT" fontName="helvetica-bold" fontSize="8.0" leftIndent="0.0"/>
            <paraStyle name="P2" fontName="Helvetica" fontSize="14.0" leading="15" spaceBefore="6.0" spaceAfter="6.0"/>
            <paraStyle name="comment" fontName="Helvetica" fontSize="14.0" leading="50" spaceBefore="0.0" spaceAfter="0.0"/>
            <paraStyle name="P1" fontName="Helvetica" fontSize="9.0" leading="12" spaceBefore="0.0" spaceAfter="1.0"/>
            <paraStyle name="terp_tblheader_Details" fontName="Helvetica-Bold" fontSize="9.0" leading="11" alignment="LEFT" spaceBefore="6.0" spaceAfter="6.0"/>
            <paraStyle name="terp_default_9" fontName="Helvetica" fontSize="9.0" leading="11" alignment="LEFT" spaceBefore="0.0" spaceAfter="0.0"/>
        </stylesheet>
        <story>"""
        surv_obj = pooler.get_pool(cr.dbname).get('survey')
        for survey in surv_obj.browse(cr,uid,ids):
            rml += """
            <blockTable colWidths='"""+_tbl_widths+"""' style="title_tbl">
                <tr><td><para style="title">""" + to_xml(tools.ustr(survey.title)) + """</para><para style="P2"><font></font></para></td></tr>
            </blockTable>"""
            if survey.note:
                rml += """
                <para style="P2"></para>
                    <blockTable colWidths='"""+_tbl_widths+"""' style="note_table">
                        <tr><td><para style="descriptive_text">""" + to_xml(tools.ustr(survey.note)) + """</para><para style="P2"><font></font></para></td></tr>
                    </blockTable>"""

            seq = 0
            for page in survey.page_ids:
                seq += 1
                rml += """
                <blockTable colWidths='"""+_tbl_widths+"""' style="page_tbl">
                    <tr><td><para style="page">"""+ tools.ustr(seq) + """. """ + to_xml(tools.ustr(page.title)) + """</para><para style="P2"><font></font></para></td></tr>
                </blockTable>"""
                if page.note:
                    rml += """<para style="P2"></para><blockTable colWidths='"""+_tbl_widths+"""' style="note_table">
                                <tr><td><para style="descriptive_text">""" + to_xml(tools.ustr(page.note or '')) + """</para></td></tr>
                            </blockTable>"""

                for que in page.question_ids:
                    cols_widhts = []
                    rml += """
                    <para style="P2"><font></font></para>
                    <blockTable colWidths='"""+_tbl_widths+"""' style="question_tbl">
                        <tr><td><para style="question">"""  + to_xml(tools.ustr(que.question)) + """</para></td></tr>
                    </blockTable>
                    <para style="P2"><font></font></para>"""
                    if que.type in ['descriptive_text']:
                        cols_widhts.append(float(_tbl_widths.replace('cm','')))
                        colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                        colWidths = colWidths + 'cm'
                        rml += """
                        <blockTable colWidths=" """ + colWidths + """ " style="ans_tbl">
                            <tr>
                                <td>
                                <para style="descriptive_text">""" + to_xml(tools.ustr(que.descriptive_text)) + """</para>
                                </td>
                            </tr>
                        </blockTable>"""

                    elif que.type in ['multiple_choice_multiple_ans','multiple_choice_only_one_ans']:
                        answer = []
                        for ans in que.answer_choice_ids:
                            answer.append(to_xml(tools.ustr((ans.answer))))

                        def divide_list(lst, n):
                            return [lst[i::n] for i in range(n)]

                        divide_list = divide_list(answer,_display_ans_in_rows)
                        for lst in divide_list:
                            if que.type == 'multiple_choice_multiple_ans':
                                if len(lst)<>0 and len(lst)<>int(round(float(len(answer))/_display_ans_in_rows,0)):
                                   lst.append('')
                            if not lst:
                               del divide_list[divide_list.index(lst):]
                        for divide in divide_list:
                            a = _divide_columns_for_matrix*len(divide)
                            b = float(_tbl_widths.replace('cm','')) - float(a)
                            cols_widhts = []

                            for div in range(0,len(divide)):
                                cols_widhts.append(float(a/len(divide)))
                                cols_widhts.append(float(b/len(divide)))
                            colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                            colWidths = colWidths +'cm'
                            rml+="""<blockTable colWidths=" """ + colWidths + """ " style="ans_tbl">
                                        <tr>"""
                            for div in range(0,len(divide)):
                               if divide[div] != '':
                                   if que.type == 'multiple_choice_multiple_ans':
                                           rml += """
                                           <td>
                                               <illustration>
                                                   <rect x="0.1cm" y="-0.4cm" width="0.5 cm" height="0.5cm" fill="no" stroke="yes"/>
                                                </illustration>
                                           </td>
                                           <td><para style="answer">""" + divide[div] + """</para></td>"""
                                   else:
                                       rml += """
                                       <td>
                                           <illustration>
                                               <circle x="0.3cm" y="-0.18cm" radius="0.23 cm" fill="no" stroke="yes"/>
                                            </illustration>
                                       </td>
                                       <td><para style="answer">""" + divide[div] + """</para></td>"""
                               else:
                                   rml += """
                                   <td></td>
                                   <td></td>"""
                            rml += """
                            </tr></blockTable>"""

                    elif que.type in ['matrix_of_choices_only_one_ans','rating_scale','matrix_of_choices_only_multi_ans','matrix_of_drop_down_menus']:
                        if len(que.column_heading_ids):
                            cols_widhts.append(float(_tbl_widths.replace('cm',''))/float(2.0))
                            for col in que.column_heading_ids:
                                cols_widhts.append(float((float(_tbl_widths.replace('cm',''))/float(2.0))/len(que.column_heading_ids)))
                        else:
                            cols_widhts.append(float(_tbl_widths.replace('cm','')))

                        tmp = 0.0
                        sum = 0.0
                        i = 0
                        if que.comment_column:
                            for col in cols_widhts:
                                if i == 0:
                                    cols_widhts[i] = cols_widhts[i]/2.0
                                    tmp = cols_widhts[i]
                                sum += col
                                i += 1
                            cols_widhts.append(round(tmp,2))
                        colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                        colWidths = colWidths+'cm'
                        matrix_ans = ['',]

                        for col in que.column_heading_ids:
                            if col.title not in matrix_ans:
                                matrix_ans.append(col.title)
                        if que.comment_column:
                            matrix_ans.append(to_xml(tools.ustr(que.column_name)))
                        rml+="""<blockTable colWidths=" """ + colWidths + """ " style="ans_tbl"><tr>"""

                        for mat_col in matrix_ans:
                            rml += """<td><para style="response">""" + to_xml(tools.ustr(mat_col)) + """</para></td>"""
                        rml += """</tr></blockTable>"""
                        i = 0
                        for ans in que.answer_choice_ids:
                            if i%2 != 0:
                                style='ans_tbl_white'
                            else:
                                style='ans_tbl_gainsboro'
                            i += 1
                            rml += """
                            <blockTable colWidths=" """ + colWidths + """ " style='"""+style+"""'>
                            <tr><td><para style="answer">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>"""
                            rec_width = float((sum-tmp)*10+100)
                            value = ""

                            if que.type in ['matrix_of_drop_down_menus']:
                                value = """ <fill color="white"/>
                                    <rect x="-0.1cm" y="-0.45cm" width='""" + tools.ustr(cols_widhts[-1] - 0.5) +"cm" + """' height="0.5cm" fill="yes" stroke="yes" round="0.1cm"/>"""
                            elif que.type in ['matrix_of_choices_only_one_ans','rating_scale']:
                                value = """ <fill color="white"/>
                                    <circle x="0.35cm" y="-0.18cm" radius="0.25 cm" fill="yes" stroke="yes"/>"""
                            else:
                                value = """ <fill color="white"/>
                                    <rect x="0.1cm" y="-0.4cm" width="0.5 cm" height="0.5cm" fill="yes" stroke="yes" round="0.1cm"/>"""
                            for mat_col in range(1,len(matrix_ans)):
                                if matrix_ans[mat_col] == que.column_name:
                                    if mat_col == 1:
                                        rml += """
                                            <td><para style="answer_left">""" + to_xml(tools.ustr(que.column_name)) + """</para></td>"""
                                    else:
                                      rml += """<td></td>"""
                                else:
                                    rml += """<td><illustration>""" + value + """</illustration></td>"""
                            rml += """</tr></blockTable>"""

                    elif que.type in ['multiple_textboxes', 'numerical_textboxes', 'date_and_time','date','multiple_textboxes_diff_type']:
                        cols_widhts.append(float(_tbl_widths.replace('cm',''))/2)
                        cols_widhts.append(float(_tbl_widths.replace('cm',''))/2)
                        colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                        colWidths = tools.ustr(colWidths) + 'cm'
                        for ans in que.answer_choice_ids:
                            rml += """<para style="P1"></para>
                            <blockTable colWidths=" """+ colWidths + """ " style="ans_tbl">
                                <tr>
                                <td><para style="answer">""" + to_xml(tools.ustr(ans.answer)) + """</para></td>
                                    <td>
                                    <illustration>
                                        <rect x="0.0cm" y="-0.5cm" width='""" + tools.ustr(str(cols_widhts[0] - 0.3) + "cm") + """' height="0.6cm" fill="no" stroke="yes"/>
                                    </illustration>
                                    </td>
                                </tr>
                            </blockTable>"""

                    elif que.type in ['comment']:
                        cols_widhts.append(float(_tbl_widths.replace('cm','')))
                        colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                        rml += """<blockTable colWidths=" """ + colWidths + """cm " style="ans_tbl">
                            <tr>
                                <td><para style="comment"><font color="white"> </font></para>
                                    <illustration>
                                        <rect x="0.1cm" y="0.3cm" width='""" + tools.ustr(str(float(colWidths) - 0.6) +'cm') + """' height="1.5cm" fill="no" stroke="yes"/>
                                    </illustration>
                                </td>
                            </tr>
                        </blockTable>"""

                    elif que.type in ['single_textbox']:
                        cols_widhts.append(float(_tbl_widths.replace('cm','')))
                        colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                        rml += """<para style="P2"><font color="white"> </font></para>
                        <blockTable colWidths=" """ + colWidths + """cm " style="ans_tbl">
                            <tr>
                                <td>
                                    <illustration>
                                        <rect x="0.2cm" y="0.3cm" width='""" + tools.ustr(str(float(colWidths) - 0.7) +'cm') + """' height="0.6cm" fill="no" stroke="yes"/>
                                    </illustration>
                                </td>
                            </tr>
                        </blockTable>"""

                    elif que.type in ['table']:
                        tbl_width = float(_tbl_widths.replace('cm',''))
                        for i in range(0,len(que.column_heading_ids)):
                            cols_widhts.append(tbl_width/float(len(que.column_heading_ids)))
                        colWidths = "cm,".join(map(tools.ustr, cols_widhts))
                        colWidths = colWidths+'cm'
                        rml += """<blockTable colWidths=" """ + colWidths + """ " style="tbl"><tr>"""
                        for col in que.column_heading_ids:
                            rml+="""<td><para style="terp_tblheader_Details">""" + to_xml(tools.ustr(col.title)) + """</para></td>"""
                        rml += """</tr></blockTable>"""
                        i = 0
                        for r in range(0,que.no_of_rows):
                            if i%2 != 0:
                                style = 'tbl_white'
                            else:
                                style = 'tbl_gainsboro'
                            i += 1
                            rml += """<blockTable colWidths=" """  + colWidths + """ " style='"""+style+"""'><tr>"""
                            for c in que.column_heading_ids:
                               rml += """
                                <td><para style="terp_default_9"><font color="white"> </font></para></td>"""
                            rml += """</tr></blockTable>"""

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

survey_form('report.survey.form', 'survey','','')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
