init_file = "custom/school_management/models/__init__.py"
with open(init_file, "r", encoding="utf-8") as f:
    text = f.read()

if "from . import planning_resource" not in text:
    text = text.replace("from . import ir_ui_view\n", "from . import ir_ui_view\nfrom . import planning_resource\n", 1)
    with open(init_file, "w", encoding="utf-8") as f:
        f.write(text)
    print("Added planning_resource to models/__init__.py")
