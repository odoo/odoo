with open('custom/school_management/static/src/school_management/dashboard_shell.js', 'r', encoding='utf-8') as f:
    c = f.read()

target = """        onWillStart(async () => {
            try {
                const isStudent = await user.hasGroup("school_management.group_school_student");
                const isStaff = (await user.hasGroup("school_management.group_school_teacher")) ||
                                (await user.hasGroup("school_management.group_school_admin")) ||
                                (await user.hasGroup("base.group_system")) ||
                                (await user.hasGroup("school_management.group_school_registrar")) ||
                                (await user.hasGroup("school_management.group_school_hod")) ||
                                (await user.hasGroup("school_management.group_school_dean"));
                if (isStudent && !isStaff) {
                    await this.action.doAction("school_management.action_student_dashboard_shell", {
                        clearBreadcrumbs: true,
                    });
                    return;
                }"""

replacement = """        onWillStart(async () => {
            try {
                const isStudent = await user.hasGroup("school_management.group_school_student");
                const isTeacher = (await user.hasGroup("school_management.group_school_teacher")) ||
                                  (await user.hasGroup("school_management.group_university_teacher"));
                const isAdminOrLeadership = (await user.hasGroup("school_management.group_school_admin")) ||
                                            (await user.hasGroup("base.group_system")) ||
                                            (await user.hasGroup("school_management.group_school_registrar")) ||
                                            (await user.hasGroup("school_management.group_school_hod")) ||
                                            (await user.hasGroup("school_management.group_school_dean"));
                if (isStudent && !isAdminOrLeadership && !isTeacher) {
                    await this.action.doAction("school_management.action_student_dashboard_shell", {
                        clearBreadcrumbs: true,
                    });
                    return;
                }
                if (isTeacher && !isAdminOrLeadership) {
                    await this.action.doAction("school_management.action_teacher_dashboard_shell", {
                        clearBreadcrumbs: true,
                    });
                    return;
                }"""

assert target in c, 'target not found'
c = c.replace(target, replacement, 1)

# Add helper methods
method_target = """    handleSidebarItemClick(item) {"""
methods_to_add = """    openTeacherWorkspace() {
        return this.action.doAction("school_management.action_teacher_dashboard_shell");
    }

    openSpreadsheetAnalytics() {
        return this.action.doAction("spreadsheet_dashboard.ir_actions_dashboard_action");
    }

    handleSidebarItemClick(item) {"""

assert method_target in c, 'method_target not found'
c = c.replace(method_target, methods_to_add, 1)

with open('custom/school_management/static/src/school_management/dashboard_shell.js', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated dashboard_shell.js successfully!')
