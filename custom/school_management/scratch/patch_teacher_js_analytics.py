with open('custom/school_management/static/src/school_management/teacher_dashboard_shell.js', 'r', encoding='utf-8') as f:
    c = f.read()

target = """    openAllExams() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Course Exams",
            res_model: "university.exam",
            domain: [["teacher_id", "=", this.state.teacher?.id]],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }"""

replacement = """    openAllExams() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Course Exams",
            res_model: "university.exam",
            domain: [["teacher_id", "=", this.state.teacher?.id]],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openSpreadsheetAnalytics() {
        return this.action.doAction("spreadsheet_dashboard.ir_actions_dashboard_action");
    }"""

assert target in c, 'target not found'
c = c.replace(target, replacement, 1)

with open('custom/school_management/static/src/school_management/teacher_dashboard_shell.js', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated teacher_dashboard_shell.js successfully!')
