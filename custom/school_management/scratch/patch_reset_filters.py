with open('static/src/school_management/teacher_dashboard_shell.js', 'r', encoding='utf-8') as f:
    c = f.read()

target = """    onExamSearch(ev) {
        this.state.examSearchQuery = ev.target.value || "";
    }"""
replacement = """    onExamSearch(ev) {
        this.state.examSearchQuery = ev.target.value || "";
    }

    resetExamFilters() {
        this.state.examFilterType = "all";
        this.state.examFilterState = "all";
        this.state.examSearchQuery = "";
    }"""

if target in c:
    c = c.replace(target, replacement, 1)
    with open('static/src/school_management/teacher_dashboard_shell.js', 'w', encoding='utf-8') as f:
        f.write(c)
    print("SUCCESS")
else:
    print("TARGET NOT FOUND")
