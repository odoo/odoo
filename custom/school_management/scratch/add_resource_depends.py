manifest_file = "custom/school_management/__manifest__.py"
with open(manifest_file, "r", encoding="utf-8") as f:
    text = f.read()

target = '        "web",\n        "spreadsheet_dashboard",\n'
replacement = '        "web",\n        "spreadsheet_dashboard",\n        "resource",\n'

if target in text and '"resource"' not in text[:text.find('"data"')]:
    text = text.replace(target, replacement, 1)
    with open(manifest_file, "w", encoding="utf-8") as f:
        f.write(text)
    print("Added resource to depends in __manifest__.py")
else:
    print("Warning: target not matched or resource already in depends")
