manifest_path = "custom/school_management/__manifest__.py"
with open(manifest_path, "r", encoding="utf-8") as f:
    content = f.read()

new_assets = """            "school_management/static/src/views/gantt/gantt_view.scss",
            "school_management/static/src/views/gantt/gantt_arch_parser.js",
            "school_management/static/src/views/gantt/gantt_model.js",
            "school_management/static/src/views/gantt/gantt_renderer.js",
            "school_management/static/src/views/gantt/gantt_renderer.xml",
            "school_management/static/src/views/gantt/gantt_controller.js",
            "school_management/static/src/views/gantt/gantt_controller.xml",
            "school_management/static/src/views/gantt/gantt_view.js",
"""

target = '"school_management/static/src/school_management/teacher_dashboard_shell.scss",\n'
if "gantt_view.js" not in content:
    content = content.replace(target, target + new_assets, 1)

with open(manifest_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Registered gantt assets in __manifest__.py")
