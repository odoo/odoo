init_file = "custom/school_management/models/__init__.py"
with open(init_file, "r", encoding="utf-8") as f:
    text = f.read()

# Remove planning_resource from top
text = text.replace("from . import planning_resource\n", "")

# Place planning_resource right after teacher
text = text.replace("from . import teacher\n", "from . import teacher\nfrom . import planning_resource\n", 1)

with open(init_file, "w", encoding="utf-8") as f:
    f.write(text)
print("Moved planning_resource after teacher in models/__init__.py")
