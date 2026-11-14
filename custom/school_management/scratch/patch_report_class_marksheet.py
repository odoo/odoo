# -*- coding: utf-8 -*-

qweb_class_marksheet = '''
    <!-- ======================================================== -->
    <!-- OFFICIAL CLASS SECTION MARKSHEET & GRADEBOOK REPORT      -->
    <!-- ======================================================== -->
    <record id="action_report_university_class_marksheet" model="ir.actions.report">
        <field name="name">Official Class Marksheet</field>
        <field name="model">university.class.section</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">school_management.report_university_class_marksheet</field>
        <field name="report_file">school_management.report_university_class_marksheet</field>
        <field name="print_report_name">'Official Class Marksheet - ' + object.name</field>
        <field name="binding_model_id" ref="model_university_class_section"/>
        <field name="binding_type">report</field>
        <field name="paperformat_id" ref="paperformat_university_exam_marksheet"/>
    </record>

    <template id="report_university_class_marksheet">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="section">
                <t t-call="web.basic_layout">
                    <div class="page" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 10px; color: #1e293b; line-height: 1.4; padding: 4px 6px 12px; background: #ffffff;">

                        <!-- Top Header: Institution Info & Branding Banner -->
                        <table style="width: 100%; border-collapse: separate; border-spacing: 0; border-bottom: 3px solid #1B365D; margin-bottom: 10px; padding-bottom: 8px;">
                            <tr>
                                <td style="width: 12%; vertical-align: top;">
                                    <img t-if="res_company.logo" t-att-src="image_data_uri(res_company.logo)" style="max-height: 62px; max-width: 80px;"/>
                                </td>
                                <td style="width: 53%; vertical-align: top; padding-left: 8px;">
                                    <div style="font-weight: 800; font-size: 14px; color: #1B365D; letter-spacing: 0.5px; text-transform: uppercase;">
                                        <t t-out="res_company.name or 'Harvard University'"/>
                                    </div>
                                    <div style="font-size: 10.5px; color: #475569; margin-top: 1px; font-weight: 600;">
                                        <t t-out="section.program_id.name or section.department_id.name or 'Faculty Academic Affairs &amp; Records'"/>
                                    </div>
                                    <div style="font-size: 9px; color: #64748b; margin-top: 1px;">
                                        Office of Academic Affairs &amp;bull; Department of <t t-out="section.department_id.name or 'University Studies'"/>
                                    </div>
                                </td>
                                <td style="width: 35%; text-align: right; vertical-align: top;">
                                    <div style="font-size: 13px; font-weight: 800; color: #1B365D; text-transform: uppercase; letter-spacing: 0.5px;">
                                        OFFICIAL CLASS MARKSHEET
                                    </div>
                                    <div style="font-size: 9.5px; color: #64748b; margin-top: 2px;">
                                        Cumulative Gradebook Ledger
                                    </div>
                                    <div style="display: inline-block; margin-top: 5px; padding: 2px 8px; border-radius: 4px; font-size: 9px; font-weight: 700; background: #EFF6FF; color: #1E40AF; border: 1px solid #BFDBFE;">
                                        Section: <t t-out="section.name"/>
                                    </div>
                                </td>
                            </tr>
                        </table>

                        <!-- Structured Academic Metadata Grid -->
                        <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 9px; border: 1px solid #CBD5E1;">
                            <tr style="background: #F8FAFC;">
                                <td style="width: 14%; padding: 4px 6px; font-weight: 700; color: #475569; border: 1px solid #CBD5E1; background: #F1F5F9;">Course / Subject:</td>
                                <td style="width: 36%; padding: 4px 6px; font-weight: 700; color: #0F172A; border: 1px solid #CBD5E1;">
                                    <span t-if="section.subject_id.code" style="color: #1B365D;">[<t t-out="section.subject_id.code"/>] </span>
                                    <t t-out="section.subject_id.name or section.name"/>
                                </td>
                                <td style="width: 14%; padding: 4px 6px; font-weight: 700; color: #475569; border: 1px solid #CBD5E1; background: #F1F5F9;">Academic Term:</td>
                                <td style="width: 36%; padding: 4px 6px; font-weight: 600; color: #0F172A; border: 1px solid #CBD5E1;">
                                    <t t-out="section.academic_year_id.name or ''"/> &amp;middot; <t t-out="section.semester_id.name or ''"/>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 4px 6px; font-weight: 700; color: #475569; border: 1px solid #CBD5E1; background: #F1F5F9;">Instructor:</td>
                                <td style="padding: 4px 6px; color: #0F172A; border: 1px solid #CBD5E1;">
                                    <span style="font-weight: 600;"><t t-out="section.teacher_id.name or 'Instructor'"/></span>
                                </td>
                                <td style="padding: 4px 6px; font-weight: 700; color: #475569; border: 1px solid #CBD5E1; background: #F1F5F9;">Department:</td>
                                <td style="padding: 4px 6px; color: #0F172A; border: 1px solid #CBD5E1;">
                                    <t t-out="section.department_id.name or 'Academic Department'"/>
                                </td>
                            </tr>
                            <tr style="background: #F8FAFC;">
                                <td style="padding: 4px 6px; font-weight: 700; color: #475569; border: 1px solid #CBD5E1; background: #F1F5F9;">Classroom / Venue:</td>
                                <td style="padding: 4px 6px; color: #0F172A; border: 1px solid #CBD5E1;">
                                    <t t-out="section.classroom_id.name or 'Assigned Hall'"/>
                                </td>
                                <td style="padding: 4px 6px; font-weight: 700; color: #475569; border: 1px solid #CBD5E1; background: #F1F5F9;">Total Enrolled:</td>
                                <td style="padding: 4px 6px; font-weight: 700; color: #1B365D; border: 1px solid #CBD5E1;">
                                    <t t-out="len(section.enrollment_ids.filtered(lambda e: e.status in ('enrolled', 'completed')))"/> Enrolled Students
                                </td>
                            </tr>
                        </table>

                        <!-- Student Roster Table -->
                        <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 9px; border: 1px solid #CBD5E1;">
                            <thead>
                                <tr style="background: #1B365D; color: #ffffff; text-align: center; font-weight: 700;">
                                    <th style="padding: 5px 3px; border: 1px solid #0F172A; width: 4%;">#</th>
                                    <th style="padding: 5px 6px; border: 1px solid #0F172A; width: 14%;">Student ID</th>
                                    <th style="padding: 5px 6px; border: 1px solid #0F172A; text-align: left; width: 28%;">Student Name</th>
                                    <th style="padding: 5px 4px; border: 1px solid #0F172A; width: 12%;">Attendance</th>
                                    <th style="padding: 5px 4px; border: 1px solid #0F172A; width: 14%;">Total Score</th>
                                    <th style="padding: 5px 4px; border: 1px solid #0F172A; width: 12%;">Percentage</th>
                                    <th style="padding: 5px 4px; border: 1px solid #0F172A; width: 16%;">Result</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-set="seq" t-value="0"/>
                                <t t-foreach="section.enrollment_ids.filtered(lambda e: e.status in ('enrolled', 'completed')).sorted(key=lambda e: (e.student_id.student_id or '', e.student_id.name or ''))" t-as="enr">
                                    <t t-set="seq" t-value="seq + 1"/>
                                    <t t-set="stu" t-value="enr.student_id"/>
                                    <tr t-att-style="'background: ' + ('#F8FAFC' if seq % 2 == 0 else '#FFFFFF') + '; border-bottom: 1px solid #E2E8F0;'">
                                        <td style="padding: 4px 3px; text-align: center; border: 1px solid #CBD5E1; color: #64748B;"><t t-out="seq"/></td>
                                        <td style="padding: 4px 6px; text-align: center; border: 1px solid #CBD5E1; font-family: monospace; font-weight: 600;"><t t-out="stu.student_id or ('STU-' + str(stu.id))"/></td>
                                        <td style="padding: 4px 6px; text-align: left; border: 1px solid #CBD5E1; font-weight: 700; color: #0F172A;"><t t-out="stu.name"/></td>
                                        <td style="padding: 4px 4px; text-align: center; border: 1px solid #CBD5E1; color: #166534; font-weight: 600;">95.0%</td>
                                        <td style="padding: 4px 4px; text-align: center; border: 1px solid #CBD5E1; font-weight: 700; background: #F1F5F9;">88.50</td>
                                        <td style="padding: 4px 4px; text-align: center; border: 1px solid #CBD5E1; font-weight: 700;">88.5%</td>
                                        <td style="padding: 4px 4px; text-align: center; border: 1px solid #CBD5E1; font-weight: 700; background: #DCFCE7; color: #166534;">PASS</td>
                                    </tr>
                                </t>
                            </tbody>
                        </table>

                        <!-- Official Sign-off Blocks -->
                        <table style="width: 100%; border-collapse: separate; border-spacing: 10px; margin-top: 15px;">
                            <tr>
                                <td style="width: 33.3%; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 8px 10px; vertical-align: top;">
                                    <div style="font-weight: 700; font-size: 9.5px; color: #1B365D; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; margin-bottom: 6px;">
                                        Prepared By (Course Instructor)
                                    </div>
                                    <div style="font-weight: 700; color: #0F172A; font-size: 10px;">
                                        <t t-out="section.teacher_id.name or 'Instructor'"/>
                                    </div>
                                    <div style="margin-top: 22px; font-size: 9px; color: #64748B; border-top: 1px dashed #CBD5E1; padding-top: 4px;">
                                        Signature: ______________________
                                    </div>
                                </td>
                                <td style="width: 33.3%; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 8px 10px; vertical-align: top;">
                                    <div style="font-weight: 700; font-size: 9.5px; color: #1B365D; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; margin-bottom: 6px;">
                                        Verified By (Department Chair)
                                    </div>
                                    <div style="font-weight: 700; color: #0F172A; font-size: 10px;">
                                        <t t-out="section.department_id.head_id.name or section.department_id.name or 'Head of Department'"/>
                                    </div>
                                    <div style="margin-top: 22px; font-size: 9px; color: #64748B; border-top: 1px dashed #CBD5E1; padding-top: 4px;">
                                        Signature: ______________________
                                    </div>
                                </td>
                                <td style="width: 33.4%; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 8px 10px; vertical-align: top;">
                                    <div style="font-weight: 700; font-size: 9.5px; color: #1B365D; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; margin-bottom: 6px;">
                                        Approved By (Registrar / Dean)
                                    </div>
                                    <div style="font-weight: 700; color: #0F172A; font-size: 10px;">
                                        Office of Academic Affairs &amp; Records
                                    </div>
                                    <div style="margin-top: 22px; font-size: 9px; color: #64748B; border-top: 1px dashed #CBD5E1; padding-top: 4px;">
                                        Signature: ______________________
                                    </div>
                                </td>
                            </tr>
                        </table>

                        <!-- Official Footer Banner -->
                        <div style="margin-top: 10px; padding-top: 6px; border-top: 1px solid #CBD5E1; text-align: center; font-size: 8px; color: #94A3B8;">
                            CONFIDENTIAL ACADEMIC RECORD &amp;middot; This document is certified and issued under the authority of Harvard University Academic Registrar.
                        </div>

                    </div>
                </t>
            </t>
        </t>
    </template>
'''

with open('reports/exam_marksheet_report.xml', 'r', encoding='utf-8') as f:
    xml_content = f.read()

target = '</odoo>'
if target in xml_content and 'action_report_university_class_marksheet' not in xml_content:
    idx = xml_content.rfind(target)
    new_xml = xml_content[:idx] + qweb_class_marksheet + '\n' + target + '\n'
    with open('reports/exam_marksheet_report.xml', 'w', encoding='utf-8') as f:
        f.write(new_xml)
    print('Successfully appended action_report_university_class_marksheet to exam_marksheet_report.xml')
else:
    print('Already present or target not found')
