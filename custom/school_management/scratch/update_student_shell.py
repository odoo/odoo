with open('static/src/school_management/student_dashboard_shell.js', 'r', encoding='utf-8') as f:
    c = f.read()

target = """    get creditsProgressWidth() {
        const credits = this.state.student?.completed_credits || 13;
        const pct = Math.min(100, Math.round((credits / 130) * 100));
        return `${pct}%`;
    }"""

replacement = """    get creditsProgressWidth() {
        const credits = this.state.student?.completed_credits || 13;
        const pct = Math.min(100, Math.round((credits / 130) * 100));
        return `${pct}%`;
    }

    get totalEnrolledCredits() {
        return (this.state.enrolledClasses || []).reduce((sum, c) => sum + (Number(c.credits) || 3), 0);
    }

    get studentStandingBadge() {
        const gpa = Number(this.studentGpaDisplay);
        if (gpa >= 3.8) return { label: "First Class Honors", class: "bg-warning-subtle text-warning border border-warning-subtle" };
        if (gpa >= 3.5) return { label: "Dean's List", class: "bg-success-subtle text-success border border-success-subtle" };
        if (gpa >= 2.0) return { label: "Good Standing", class: "bg-info-subtle text-info border border-info-subtle" };
        return { label: "Academic Advisory", class: "bg-danger-subtle text-danger border border-danger-subtle" };
    }

    get creditsCompletionPercent() {
        const credits = Number(this.state.student?.completed_credits) || 13;
        return Math.min(100, Math.round((credits / 130) * 100));
    }"""

if target in c:
    c = c.replace(target, replacement, 1)
    with open('static/src/school_management/student_dashboard_shell.js', 'w', encoding='utf-8') as f:
        f.write(c)
    print("SUCCESS: Added getters to student_dashboard_shell.js")
else:
    print("ERROR: Target not found")
