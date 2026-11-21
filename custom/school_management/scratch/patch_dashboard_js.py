js_path = 'custom/school_management/static/src/school_management/teacher_dashboard_shell.js'
with open(js_path, 'r', encoding='utf-8') as f:
    text = f.read()

old_js = """    downloadExamMarksheet(examId) {
        if (!examId) return;
        window.open(`/university/marksheet/${examId}/xlsx`, "_blank");
    }"""

new_js = """    downloadExamMarksheet(examId) {
        if (!examId) return;
        window.open(`/university/marksheet/${examId}/xlsx`, "_blank");
    }

    downloadExamMarksheetPdf(examId) {
        if (!examId) return;
        window.open(`/university/marksheet/${examId}/pdf`, "_blank");
    }"""

assert old_js in text, "old_js not found!"
text = text.replace(old_js, new_js, 1)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated teacher_dashboard_shell.js successfully")

xml_path = 'custom/school_management/static/src/school_management/teacher_dashboard_shell.xml'
with open(xml_path, 'r', encoding='utf-8') as f:
    x_text = f.read()

old_btn = """                                                            <button type="button" class="btn btn-outline-success btn-sm py-1 px-2 fw-semibold d-inline-flex align-items-center gap-1 shadow-2xs"
                                                                    t-on-click="() => this.downloadExamMarksheet(exam.id)"
                                                                    title="Export Harvard Official Excel Marksheet">
                                                                <i class="fa fa-file-excel-o text-success" aria-hidden="true"/>
                                                                <span>Marksheet</span>
                                                            </button>"""

new_btn = """                                                            <button type="button" class="btn btn-outline-danger btn-sm py-1 px-2 fw-semibold d-inline-flex align-items-center gap-1 shadow-2xs"
                                                                    t-on-click="() => this.downloadExamMarksheetPdf(exam.id)"
                                                                    title="Print Official PDF Marksheet">
                                                                <i class="fa fa-file-pdf-o text-danger" aria-hidden="true"/>
                                                                <span>PDF</span>
                                                            </button>
                                                            <button type="button" class="btn btn-outline-success btn-sm py-1 px-2 fw-semibold d-inline-flex align-items-center gap-1 shadow-2xs"
                                                                    t-on-click="() => this.downloadExamMarksheet(exam.id)"
                                                                    title="Export Harvard Official Excel Marksheet">
                                                                <i class="fa fa-file-excel-o text-success" aria-hidden="true"/>
                                                                <span>Excel</span>
                                                            </button>"""

assert old_btn in x_text, "old_btn not found!"
x_text = x_text.replace(old_btn, new_btn, 1)

old_side = """                                <div class="d-flex align-items-center gap-1 flex-shrink-0">
                                    <button type="button" class="btn btn-sm btn-outline-success p-1 py-0 very-small"
                                            t-on-click="() => this.downloadExamMarksheet(rexam.id)"
                                            title="Export Excel Marksheet">
                                        <i class="fa fa-download"/>
                                    </button>
                                    <button type="button" class="btn btn-sm btn-outline-primary p-1 py-0 very-small"
                                            t-on-click="() => this.openExamScores(rexam.id)"
                                            title="Grade Scores">
                                        <i class="fa fa-pencil"/>
                                    </button>
                                </div>"""

new_side = """                                <div class="d-flex align-items-center gap-1 flex-shrink-0">
                                    <button type="button" class="btn btn-sm btn-outline-danger p-1 py-0 very-small"
                                            t-on-click="() => this.downloadExamMarksheetPdf(rexam.id)"
                                            title="Print PDF Marksheet">
                                        <i class="fa fa-file-pdf-o"/>
                                    </button>
                                    <button type="button" class="btn btn-sm btn-outline-success p-1 py-0 very-small"
                                            t-on-click="() => this.downloadExamMarksheet(rexam.id)"
                                            title="Export Excel Marksheet">
                                        <i class="fa fa-download"/>
                                    </button>
                                    <button type="button" class="btn btn-sm btn-outline-primary p-1 py-0 very-small"
                                            t-on-click="() => this.openExamScores(rexam.id)"
                                            title="Grade Scores">
                                        <i class="fa fa-pencil"/>
                                    </button>
                                </div>"""

assert old_side in x_text, "old_side not found!"
x_text = x_text.replace(old_side, new_side, 1)

with open(xml_path, 'w', encoding='utf-8') as f:
    f.write(x_text)

print("Updated teacher_dashboard_shell.xml successfully")
