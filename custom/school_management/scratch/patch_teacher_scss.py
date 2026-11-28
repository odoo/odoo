with open("static/src/school_management/teacher_dashboard_shell.scss", "r", encoding="utf-8") as f:
    scss = f.read()

target = """    // Sidebar Modular Cards
    .o_sidebar_card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.15rem;
        box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04);
        margin-bottom: 1.25rem;

        &:last-child {
            margin-bottom: 0;
        }
    }

}"""

replacement = """    // Sidebar Modular Cards
    .o_sidebar_card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.15rem;
        box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04);
        margin-bottom: 1.25rem;

        &:last-child {
            margin-bottom: 0;
        }
    }

    // Examination & Marksheet Hub Enhancements
    .o_exam_kpi_card {
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        &:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px -2px rgba(15, 23, 42, 0.08) !important;
            border-color: #cbd5e1;
        }
    }

    .shadow-2xs {
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
    }

}"""

if target in scss:
    scss = scss.replace(target, replacement, 1)
    with open("static/src/school_management/teacher_dashboard_shell.scss", "w", encoding="utf-8") as f:
        f.write(scss)
    print("SCSS patched successfully!")
else:
    print("Target not found in SCSS!")
