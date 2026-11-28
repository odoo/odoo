init_file = "custom/school_management/models/__init__.py"
with open(init_file, "r", encoding="utf-8") as f:
    text = f.read()

if "from . import ir_ui_view" not in text:
    text = "from . import ir_ui_view\n" + text
    with open(init_file, "w", encoding="utf-8") as f:
        f.write(text)
    print("Added ir_ui_view to models/__init__.py")
else:
    print("ir_ui_view already in models/__init__.py")
