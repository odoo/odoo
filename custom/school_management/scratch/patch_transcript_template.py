path = r"custom\school_management\reports\academic_report_templates.xml"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = '    <template id="report_university_transcript_document">'
end_marker = '</odoo>'

idx_start = content.find(start_marker)
idx_end = content.rfind(end_marker)
assert idx_start != -1 and idx_end != -1, "Markers not found"

new_template = '''    <template id="report_university_transcript_document">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="transcript">
                <t t-set="o" t-value="transcript"/>
                <t t-call="web.basic_layout">
                    <div class="page" style="color: #111; line-height: 1.35; padding: 10px 5px; background: #fff;">
                        <style type="text/css">
                            .page { font-family: 'Noto Sans', 'Noto Sans Khmer', Arial, sans-serif; font-size: 11px; }
                            .page table { border-collapse: collapse; }
                            .transcript-watermark { position: fixed; top: 38%; left: 20%; z-index: 0; color: #666; opacity: 0.10; font-size: 86px; font-weight: bold; -webkit-transform: rotate(-32deg); transform: rotate(-32deg); }
                            .transcript-content { position: relative; z-index: 1; }
                        </style>
                        <div t-if="transcript.state != 'approved'" class="transcript-watermark">DRAFT</div>
                        <div class="transcript-content">
                            <table style="width: 100%; margin-bottom: 8px;">
                                <tr>
                                    <td style="width: 14%; vertical-align: top;"><img src="/school_management/static/src/img/university_logo.png" style="max-height: 70px; max-width: 85px;"/></td>
                                    <td style="width: 56%; vertical-align: top; padding-left: 6px;">
                                        <div style="font-weight: bold; font-size: 13px; text-transform: uppercase;"><t t-out="o.company_id.name or res_company.name"/></div>
                                        <div style="font-size: 12px; font-weight: bold; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Academic Transcript</div>
                                        <div style="font-size: 10px; color: #444; margin-top: 2px;">Program: <t t-out="transcript.program_id.name or 'Degree Program'"/></div>
                                    </td>
                                    <td style="width: 30%; vertical-align: top; text-align: right; font-size: 10px; line-height: 1.35;">
                                        <div style="font-weight: bold;"><t t-out="o.company_id.name or res_company.name"/></div>
                                        <div t-if="company_address"><t t-out="company_address"/></div>
                                        <div t-elif="o.company_id.city or res_company.city"><t t-out="o.company_id.city or res_company.city"/>, <t t-out="(o.company_id.country_id or res_company.country_id).name or ''"/></div>
                                        <div t-if="o.company_id.website or res_company.website"><t t-out="o.company_id.website or res_company.website"/></div>
                                    </td>
                                </tr>
                            </table>

                            <div style="font-weight: bold; font-size: 11px; margin-bottom: 10px;">Date Issued: <span t-out="context_timestamp(datetime.datetime.now()).strftime('%B %d, %Y')"/></div>

                            <table style="width: 100%; font-size: 11px; margin-bottom: 12px; line-height: 1.45;">
                                <tr>
                                    <td style="width: 16%; color: #222;">Name:</td>
                                    <td style="width: 34%; font-weight: bold;"><t t-out="transcript.student_id.name"/></td>
                                    <td style="width: 18%; color: #222;">Date Graduated:</td>
                                    <td style="width: 32%; font-weight: bold;"><t t-out="graduation_date.strftime('%B %d, %Y') if graduation_date else 'In progress'"/></td>
                                </tr>
                                <tr>
                                    <td style="color: #222;">Student ID:</td>
                                    <td style="font-weight: bold;"><t t-out="transcript.student_id.student_id or ''"/></td>
                                    <td style="color: #222;">Emergency Contact:</td>
                                    <td style="font-weight: bold;"><t t-out="transcript.student_id.emergency_contact_name or '—'"/></td>
                                </tr>
                                <tr t-if="transcript.student_id.date_of_birth or transcript.student_id.address">
                                    <td style="color: #222;">Birthdate:</td><td><t t-out="transcript.student_id.date_of_birth.strftime('%b %d, %Y') if transcript.student_id.date_of_birth else '—'"/></td>
                                    <td style="color: #222;">Address:</td><td><t t-out="transcript.student_id.address or '—'"/></td>
                                </tr>
                                <tr t-if="transcript.student_id.gender">
                                    <td style="color: #222;">Gender:</td>
                                    <td><t t-if="transcript.student_id.gender == 'male'">Male</t><t t-elif="transcript.student_id.gender == 'female'">Female</t><t t-else=\"\">Other</t></td>
                                    <td style="color: #222;">Reference:</td>
                                    <td style="font-weight: bold;"><t t-out="transcript.name"/></td>
                                </tr>
                                <tr t-if="not transcript.student_id.gender">
                                    <td style="color: #222;">Reference:</td>
                                    <td colspan="3" style="font-weight: bold;"><t t-out="transcript.name"/></td>
                                </tr>
                            </table>

                            <table style="width: 100%; font-size: 10px; margin-bottom: 12px; line-height: 1.35;">
                                <tr>
                                    <td style="width: 50%; vertical-align: top; padding-right: 15px;">
                                        <div style="font-weight: bold; margin-bottom: 3px;">Requirements</div>
                                        <div>Program: <t t-out="transcript.program_id.name or 'Degree Program'"/></div>
                                        <div t-if="passing_line">Passing Grade: Minimum <t t-out="passing_line.name"/> (<t t-out="'%.2f' % passing_line.grade_point"/>) / <t t-out="'%.2f' % passing_line.min_score"/>%</div>
                                        <div t-else=\"\">Passing Grade: Not configured</div>
                                        <div style="font-style: italic; margin-top: 2px;">Degree Requirement: Minimum <t t-out="'%d' % credits_required"/> credits required for completion.</div>
                                        <div style="font-weight: bold; margin-top: 4px;">Degree Progress: <t t-out="'%.2f' % total_credits"/> / <t t-out="'%d' % credits_required"/> credits earned</div>
                                        <t t-if="attendance_rate is not False"><div style="font-weight: bold; margin-top: 6px; margin-bottom: 2px;">Attendance</div><div>Attendance: <t t-out="'%.1f' % attendance_rate"/>%</div></t>
                                        <t t-else=\"\"><div style="font-weight: bold; margin-top: 6px; margin-bottom: 2px;">Academic Standing</div><div><t t-if=\"transcript.academic_standing == 'dean_list'\">Dean's List</t><t t-elif=\"transcript.academic_standing == 'good'\">Good Standing</t><t t-else=\"\">Academic Probation</t></div></t>
                                    </td>
                                    <td style="width: 50%; vertical-align: top; padding-left: 10px;">
                                        <div style="font-weight: bold; text-align: right; margin-bottom: 3px;">Grading Scale</div>
                                        <table style="width: 100%; font-size: 10px; text-align: right;">
                                            <thead><tr style="border-bottom: 1px solid #111;"><th style="text-align: left; padding: 2px 3px;">Grade</th><th style="padding: 2px 3px;">Standard</th><th t-if="has_honors_grade_point" style="padding: 2px 3px;">Honors</th><th style="padding: 2px 3px;">Range (%)</th></tr></thead>
                                            <tbody><t t-foreach="grade_lines" t-as="grade_line"><tr><td style="text-align: left; font-weight: bold; padding: 2px 3px;"><t t-out="grade_line.name"/></td><td style="padding: 2px 3px;"><t t-out="'%.2f' % grade_line.grade_point"/></td><td t-if="has_honors_grade_point" style="padding: 2px 3px;"><t t-out="'%.2f' % grade_line.honors_grade_point"/></td><td style="padding: 2px 3px;"><t t-out="'%.2f - %.2f' % (grade_line.min_score, grade_line.max_score)"/>%</td></tr></t></tbody>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <t t-foreach="years_data" t-as="y_info">
                                <div style="border: 1.5px solid #000; margin-bottom: 12px; page-break-inside: avoid;">
                                    <div style="border-bottom: 1.5px solid #000; padding: 4px 0; text-align: center; font-weight: bold; font-size: 11px;"><t t-out="'Year %d - %s' % (y_info['year_number'], y_info['year'].name)"/></div>
                                    <table style="width: 100%; table-layout: fixed; font-size: 10px; border-collapse: collapse;"><tr>
                                        <td style="width: 50%; vertical-align: top; border-right: 1.5px solid #000; padding: 8px 10px;">
                                            <div style="font-weight: bold; margin-bottom: 4px;">First Semester</div>
                                            <table style="width: 100%; table-layout: fixed; font-size: 10px; border-collapse: collapse;"><thead><tr style="border-bottom: 1px solid #999;"><th style="text-align: left; padding: 2px 3px;">Course</th><th style="text-align: center; width: 14%; padding: 2px 3px;">Grade</th><th style="text-align: right; width: 20%; padding: 2px 3px;">Credits</th></tr></thead><tbody>
                                                <t t-if="y_info['s1_lines']"><t t-foreach="y_info['s1_lines']" t-as="l"><tr style="line-height: 1.35;"><td style="padding: 2px 3px; vertical-align: middle;"><t t-if="l.subject_id.code"><t t-out="l.subject_id.code"/> - </t><t t-out="l.subject_id.name"/><t t-if="l.id in repeated_line_ids"><span style="font-size: 9px; color: #555;"> (R)</span></t></td><td style="text-align: center; font-weight: bold; padding: 2px 3px; vertical-align: middle;"><t t-out="l.grade or '-'"/></td><td style="text-align: right; padding: 2px 3px; vertical-align: middle;"><t t-out="'%.2f' % (l.credits or 0.0)"/></td></tr></t></t>
                                                <t t-else=\"\"><tr><td colspan=\"3\" style=\"font-style: italic; color: #555; padding: 6px 3px; text-align: center;\">-- <t t-out=\"y_info['s1_status']\"/> --</td></tr></t>
                                            </tbody></table>
                                            <table style="width: 100%; margin-top: 8px; border-top: 1px dashed #aaa; padding-top: 3px; font-size: 10px;">
                                                <tr>
                                                    <td style="text-align: left; padding: 1px 0;">Semester GPA: </td>
                                                    <td style="text-align: right; font-weight: bold; padding: 1px 0;"><t t-out="'%.2f' % y_info['s1_gpa'] if y_info['s1_lines'] else '--'"/></td>
                                                </tr>
                                                <tr>
                                                    <td style="text-align: left; padding: 1px 0;">Semester Credits: </td>
                                                    <td style="text-align: right; font-weight: bold; padding: 1px 0;"><t t-out="'%.2f' % y_info['s1_credits']"/></td>
                                                </tr>
                                            </table>
                                        </td>
                                        <td style="width: 50%; vertical-align: top; padding: 8px 10px;">
                                            <div style="font-weight: bold; margin-bottom: 4px;">Second Semester</div>
                                            <table style="width: 100%; table-layout: fixed; font-size: 10px; border-collapse: collapse;"><thead><tr style="border-bottom: 1px solid #999;"><th style="text-align: left; padding: 2px 3px;">Course</th><th style="text-align: center; width: 14%; padding: 2px 3px;">Grade</th><th style="text-align: right; width: 20%; padding: 2px 3px;">Credits</th></tr></thead><tbody>
                                                <t t-if="y_info['s2_lines']"><t t-foreach="y_info['s2_lines']" t-as="l"><tr style="line-height: 1.35;"><td style="padding: 2px 3px; vertical-align: middle;"><t t-if="l.subject_id.code"><t t-out="l.subject_id.code"/> - </t><t t-out="l.subject_id.name"/><t t-if="l.id in repeated_line_ids"><span style="font-size: 9px; color: #555;"> (R)</span></t></td><td style="text-align: center; font-weight: bold; padding: 2px 3px; vertical-align: middle;"><t t-out="l.grade or '-'"/></td><td style="text-align: right; padding: 2px 3px; vertical-align: middle;"><t t-out="'%.2f' % (l.credits or 0.0)"/></td></tr></t></t>
                                                <t t-else=\"\"><tr><td colspan=\"3\" style=\"font-style: italic; color: #555; padding: 6px 3px; text-align: center;\">-- <t t-out=\"y_info['s2_status']\"/> --</td></tr></t>
                                            </tbody></table>
                                            <table style="width: 100%; margin-top: 8px; border-top: 1px dashed #aaa; padding-top: 3px; font-size: 10px;">
                                                <tr>
                                                    <td style="text-align: left; padding: 1px 0;">Semester GPA: </td>
                                                    <td style="text-align: right; font-weight: bold; padding: 1px 0;"><t t-out="'%.2f' % y_info['s2_gpa'] if y_info['s2_lines'] else '--'"/></td>
                                                </tr>
                                                <tr>
                                                    <td style="text-align: left; padding: 1px 0;">Semester Credits: </td>
                                                    <td style="text-align: right; font-weight: bold; padding: 1px 0;"><t t-out="'%.2f' % y_info['s2_credits']"/></td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr></table>
                                </div>
                            </t>

                            <table style="width: 100%; font-size: 10px; margin-top: 15px; page-break-inside: avoid;"><tr>
                                <td style="width: 45%; vertical-align: top;">
                                    <div style="font-weight: bold; margin-bottom: 4px; text-transform: uppercase;">Academic Information</div>
                                    <table style="width: 95%; font-size: 10px; line-height: 1.5;">
                                        <tr t-if="has_honors_grade_point">
                                            <td style="width: 65%;">Cumulative Weighted GPA</td>
                                            <td style="width: 35%; text-align: right; font-weight: bold;"><t t-out="'%.2f' % weighted_gpa"/> / <t t-out="'%.2f' % weighted_max"/></td>
                                        </tr>
                                        <tr>
                                            <td style="width: 65%;">Cumulative GPA</td>
                                            <td style="width: 35%; text-align: right; font-weight: bold;"><t t-out="'%.2f' % unweighted_gpa"/> / <t t-out="'%.2f' % unweighted_max"/></td>
                                        </tr>
                                        <tr>
                                            <td>Degree Progress</td>
                                            <td style="text-align: right; font-weight: bold;"><t t-out="'%.2f' % total_credits"/> / <t t-out="'%d' % credits_required"/> credits earned</td>
                                        </tr>
                                        <tr>
                                            <td>Academic Standing</td>
                                            <td style="text-align: right; font-weight: bold;">
                                                <span t-if="transcript.academic_standing == 'dean_list'">Dean's List</span>
                                                <span t-elif="transcript.academic_standing == 'good'">Good Standing</span>
                                                <span t-else=\"\">Academic Probation</span>
                                            </td>
                                        </tr>
                                    </table>
                                    <div style="font-weight: bold; margin-top: 8px; margin-bottom: 2px;">Record Verification</div>
                                    <div style="color: #444; font-size: 9px;">Official academic transcript generated from certified institution records.</div>
                                    <div style="color: #444; font-size: 10px; margin-top: 2px;">Verification Code: <strong style="letter-spacing: 1px;"><t t-out="transcript.verification_code or 'ACADEMIC-RECORD'"/></strong></div>
                                </td>
                                <td style="width: 25%; vertical-align: bottom; text-align: center; padding-bottom: 5px;"><div style="font-weight: bold; margin-bottom: 5px; font-size: 10px;">Seal:</div><div style="width: 80px; height: 80px; border: 1.5px dashed #444; border-radius: 50%; margin: 0 auto; text-align: center; font-size: 9px; font-weight: bold; color: #444; line-height: 1.2; padding-top: 24px;">SAMPLE<br/>SEAL</div></td>
                                <td style="width: 30%; vertical-align: bottom; text-align: center;"><div style="font-size: 9px; color: #444; margin-bottom: 4px;">Signature</div><div style="border-bottom: 1.5px solid #000; width: 100%; margin-bottom: 4px;"></div><div style="font-weight: bold; font-size: 11px;">Executive Director</div><div style="font-size: 9px; color: #444;"><t t-out="o.company_id.name or res_company.name"/></div></td>
                            </tr></table>
                            <t t-if="has_honors_grade_point">
                                <div style="text-align: center; font-size: 10px; color: #444; margin-top: 8px;">Grading legend: Standard GPA on 4.00 scale; Honors courses weighted up to <t t-out="'%.2f' % weighted_max"/>. Passing grade defined per academic program. (R) indicates repeated course.</div>
                            </t>
                            <t t-else=\"\">
                                <div style="text-align: center; font-size: 10px; color: #444; margin-top: 8px;">Grading legend: Standard GPA on 4.00 scale. Passing grade defined per academic program. (R) indicates repeated course.</div>
                            </t>
                            <div style="text-align: center; font-size: 10px; color: #222; margin-top: 4px; font-weight: bold; letter-spacing: 0.5px;">SAMPLE DOCUMENT - NOT AN OFFICIAL RECORD</div>
                            <div style="text-align: center; font-size: 10px; color: #555; margin-top: 6px;">1 of 1</div>
                        </div>
                    </div>
                </t>
            </t>
        </t>
    </template>
'''

content = content[:idx_start] + new_template + content[idx_end:]
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("academic_report_templates.xml patched successfully!")
