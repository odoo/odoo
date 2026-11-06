NEW_KANBAN = '''    <!-- KANBAN VIEW -->
    <record id="view_university_assessment_category_kanban" model="ir.ui.view">
        <field name="name">university.assessment.category.kanban</field>
        <field name="model">university.assessment.category</field>
        <field name="arch" type="xml">
            <kanban limit="10" sample="1" class="o_university_assessment_category_kanban">
                <field name="id"/>
                <field name="name"/>
                <field name="code"/>
                <field name="weight"/>
                <field name="evaluation_type"/>
                <field name="icon"/>
                <field name="color"/>
                <field name="active"/>
                <field name="assignment_count"/>
                <field name="result_count"/>
                <field name="avg_score"/>
                <field name="passing_rate"/>
                <field name="description"/>
                <templates>
                    <t t-name="card" class="o_assessment_cat_card p-3 d-flex flex-column justify-content-between h-100">
                        <div>
                            <!-- Header: Icon, Category Name, Code, and Weight Badge -->
                            <div class="d-flex align-items-start justify-content-between gap-2 mb-2">
                                <div class="d-flex align-items-center gap-2 min-w-0">
                                    <t t-if="record.evaluation_type.raw_value == 'exam'">
                                        <div class="o_category_icon_tile o_category_exam shadow-sm flex-shrink-0">
                                            <i class="fa fa-graduation-cap" title="Examination" aria-hidden="true"/>
                                        </div>
                                    </t>
                                    <t t-elif="record.evaluation_type.raw_value == 'quiz'">
                                        <div class="o_category_icon_tile o_category_quiz shadow-sm flex-shrink-0">
                                            <i class="fa fa-question-circle" title="Quiz" aria-hidden="true"/>
                                        </div>
                                    </t>
                                    <t t-elif="record.evaluation_type.raw_value == 'attendance'">
                                        <div class="o_category_icon_tile o_category_attendance shadow-sm flex-shrink-0">
                                            <i class="fa fa-calendar-check-o" title="Attendance" aria-hidden="true"/>
                                        </div>
                                    </t>
                                    <t t-elif="record.evaluation_type.raw_value == 'practical'">
                                        <div class="o_category_icon_tile o_category_practical shadow-sm flex-shrink-0">
                                            <i class="fa fa-flask" title="Practical" aria-hidden="true"/>
                                        </div>
                                    </t>
                                    <t t-else="">
                                        <div class="o_category_icon_tile o_category_coursework shadow-sm flex-shrink-0">
                                            <i class="fa fa-file-text-o" title="Coursework" aria-hidden="true"/>
                                        </div>
                                    </t>
                                    <div class="min-w-0 flex-grow-1">
                                        <strong class="fs-6 fw-bold text-dark text-truncate d-block" t-att-title="record.name.value">
                                            <field name="name"/>
                                        </strong>
                                        <div class="d-flex align-items-center gap-1 mt-1">
                                            <span class="badge bg-light text-secondary border px-1 py-0 fs-7 fw-semibold font-monospace">
                                                <field name="code"/>
                                            </span>
                                            <span class="text-muted small text-truncate">
                                                <field name="evaluation_type"/>
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div class="text-end flex-shrink-0">
                                    <div class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 fs-6 fw-bold">
                                        <field name="weight"/>%
                                    </div>
                                    <div class="text-muted small" style="font-size: 0.7rem;">Weight</div>
                                </div>
                            </div>

                            <!-- Weight Progress Bar -->
                            <div class="progress my-2" style="height: 5px; background-color: #f1f5f9;">
                                <div class="progress-bar rounded" role="progressbar"
                                     t-attf-style="width: #{record.weight.raw_value || 0}%; background-color: #{record.evaluation_type.raw_value == 'exam' ? '#dc2626' : (record.evaluation_type.raw_value == 'quiz' ? '#7c3aed' : (record.evaluation_type.raw_value == 'attendance' ? '#16a34a' : '#2563eb'))};"
                                     t-att-aria-valuenow="record.weight.raw_value"
                                     aria-valuemin="0" aria-valuemax="100"/>
                            </div>

                            <!-- Description Snippet -->
                            <div class="text-muted small my-2" style="font-size: 0.8rem; line-height: 1.35; min-height: 2.7rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" t-att-title="record.description.value">
                                <t t-if="record.description.raw_value">
                                    <i class="fa fa-info-circle text-info me-1" title="Policy"/>
                                    <field name="description"/>
                                </t>
                                <t t-else="">
                                    <span class="text-muted fst-italic">Standard university assessment criteria and scoring policy apply.</span>
                                </t>
                            </div>

                            <!-- 2x2 Metric Cards Grid -->
                            <div class="row g-2 my-2 pt-2 border-top">
                                <div class="col-6">
                                    <button type="object" name="action_view_assignments" class="btn btn-sm btn-light border w-100 p-2 text-start d-flex align-items-center justify-content-between rounded-2 shadow-none o_metric_box" title="View Linked Assignments">
                                        <div class="d-flex align-items-center gap-2 min-w-0">
                                            <div class="o_metric_icon rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center">
                                                <i class="fa fa-file-text-o fs-7"/>
                                            </div>
                                            <div class="min-w-0">
                                                <div class="fw-bold text-dark fs-6 lh-1"><field name="assignment_count"/></div>
                                                <div class="text-muted small text-truncate" style="font-size: 0.7rem;">Assignments</div>
                                            </div>
                                        </div>
                                        <i class="fa fa-chevron-right text-muted fs-8 ms-1"/>
                                    </button>
                                </div>
                                <div class="col-6">
                                    <button type="object" name="action_view_results" class="btn btn-sm btn-light border w-100 p-2 text-start d-flex align-items-center justify-content-between rounded-2 shadow-none o_metric_box" title="View Assessment Results">
                                        <div class="d-flex align-items-center gap-2 min-w-0">
                                            <div class="o_metric_icon rounded-circle bg-success-subtle text-success d-flex align-items-center justify-content-center">
                                                <i class="fa fa-check-circle fs-7"/>
                                            </div>
                                            <div class="min-w-0">
                                                <div class="fw-bold text-dark fs-6 lh-1"><field name="result_count"/></div>
                                                <div class="text-muted small text-truncate" style="font-size: 0.7rem;">Records</div>
                                            </div>
                                        </div>
                                        <i class="fa fa-chevron-right text-muted fs-8 ms-1"/>
                                    </button>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 border rounded-2 bg-light d-flex align-items-center gap-2">
                                        <div class="o_metric_icon rounded-circle bg-info-subtle text-info d-flex align-items-center justify-content-center">
                                            <i class="fa fa-line-chart fs-7"/>
                                        </div>
                                        <div class="min-w-0">
                                            <div class="fw-bold text-dark fs-6 lh-1"><field name="avg_score"/>%</div>
                                            <div class="text-muted small text-truncate" style="font-size: 0.7rem;">Avg Score</div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 border rounded-2 bg-light d-flex align-items-center gap-2">
                                        <div class="o_metric_icon rounded-circle bg-warning-subtle text-warning d-flex align-items-center justify-content-center">
                                            <i class="fa fa-trophy fs-7"/>
                                        </div>
                                        <div class="min-w-0">
                                            <div class="fw-bold text-dark fs-6 lh-1"><field name="passing_rate"/>%</div>
                                            <div class="text-muted small text-truncate" style="font-size: 0.7rem;">Pass Rate</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Card Footer -->
                        <footer class="d-flex align-items-center justify-content-between pt-2 mt-auto border-top">
                            <div class="d-flex align-items-center gap-2">
                                <button type="object" name="action_view_assignments" class="btn btn-link btn-sm p-0 text-decoration-none fw-semibold text-primary">
                                    <span>View Work</span>
                                    <i class="fa fa-arrow-right ms-1" style="font-size: 0.75rem;" title="View Work"/>
                                </button>
                                <span class="text-muted small">|</span>
                                <button type="object" name="action_view_results" class="btn btn-link btn-sm p-0 text-decoration-none fw-semibold text-success">
                                    <span>Scores</span>
                                    <i class="fa fa-table ms-1" style="font-size: 0.75rem;" title="Score Records"/>
                                </button>
                            </div>
                            <div>
                                <t t-if="record.active.raw_value">
                                    <span class="badge rounded-pill bg-success-subtle text-success border border-success-subtle px-2 py-1 fs-7 fw-medium">Active</span>
                                </t>
                                <t t-else="">
                                    <span class="badge rounded-pill bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1 fs-7 fw-medium">Archived</span>
                                </t>
                            </div>
                        </footer>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>'''

file_path = r'C:\Odoo\odoo\custom\school_management\views\grading_views.xml'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = '    <!-- KANBAN VIEW -->\n    <record id="view_university_assessment_category_kanban" model="ir.ui.view">'
end_marker = '    </record>\n\n    <record id="view_university_assessment_category_form" model="ir.ui.view">'

pos_start = content.find(start_marker)
pos_end = content.find(end_marker)

if pos_start == -1 or pos_end == -1:
    print('ERROR: markers not found!')
else:
    new_content = content[:pos_start] + NEW_KANBAN + content[pos_end + len('    </record>'):]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('SUCCESS: updated grading_views.xml!')
