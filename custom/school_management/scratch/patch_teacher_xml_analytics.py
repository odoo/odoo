with open('custom/school_management/static/src/school_management/teacher_dashboard_shell.xml', 'r', encoding='utf-8') as f:
    c = f.read()

target1 = """                                    <div class="d-flex gap-2">
                                        <button type="button" class="btn btn-outline-primary btn-sm"
                                                t-on-click="() => this.openAllExams()">
                                            <i class="fa fa-external-link me-1"/>Manage All Exams
                                        </button>
                                    </div>"""

replacement1 = """                                    <div class="d-flex gap-2">
                                        <button type="button" class="btn btn-outline-success btn-sm"
                                                t-on-click="() => this.openSpreadsheetAnalytics()">
                                            <i class="fa fa-table me-1"/>Academic &amp; Student Analytics
                                        </button>
                                        <button type="button" class="btn btn-outline-primary btn-sm"
                                                t-on-click="() => this.openAllExams()">
                                            <i class="fa fa-external-link me-1"/>Manage All Exams
                                        </button>
                                    </div>"""

assert target1 in c, 'target1 not found'
c = c.replace(target1, replacement1, 1)

target2 = """                        <button type="button" class="btn btn-outline-secondary btn-sm"
                                t-on-click="() => this.setActiveTab('exams')">
                            <i class="fa fa-file-excel-o me-1 text-success"/>Exams &amp; Marksheets
                        </button>"""

replacement2 = """                        <button type="button" class="btn btn-outline-secondary btn-sm"
                                t-on-click="() => this.setActiveTab('exams')">
                            <i class="fa fa-file-excel-o me-1 text-success"/>Exams &amp; Marksheets
                        </button>
                        <button type="button" class="btn btn-outline-success btn-sm"
                                t-on-click="() => this.openSpreadsheetAnalytics()">
                            <i class="fa fa-table me-1"/>Spreadsheet Analytics
                        </button>"""

assert target2 in c, 'target2 not found'
c = c.replace(target2, replacement2, 1)

with open('custom/school_management/static/src/school_management/teacher_dashboard_shell.xml', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated teacher_dashboard_shell.xml successfully!')
