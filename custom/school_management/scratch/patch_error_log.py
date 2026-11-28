with open("static/src/school_management/teacher_dashboard_shell.js", "r", encoding="utf-8") as f:
    c = f.read()

target = 'this.state.error = error.message || "Unable to load your teacher dashboard.";'
replacement = 'console.error("TEACHER DASHBOARD LOAD ERROR:", error); this.state.error = (error.data && error.data.message) || error.message || String(error);'

if target in c:
    c = c.replace(target, replacement, 1)
    with open("static/src/school_management/teacher_dashboard_shell.js", "w", encoding="utf-8") as f:
        f.write(c)
    print("PATCH SUCCESS")
else:
    print("TARGET NOT FOUND")
