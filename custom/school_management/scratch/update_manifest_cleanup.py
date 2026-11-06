manifest_path = "custom/school_management/__manifest__.py"
with open(manifest_path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove data entry
content = content.replace('        "data/timetable_config_param.xml",\n', "")

# Remove assets entries
to_remove = [
    '            "school_management/static/src/scss/native_schedule.scss",\n',
    '            "school_management/static/src/schedule/university_schedule.js",\n',
    '            "school_management/static/src/schedule/university_schedule.xml",\n',
    '            "school_management/static/src/schedule/university_schedule.scss",\n',
    '            "school_management/static/src/timetable/timetable_popover.js",\n',
    '            "school_management/static/src/timetable/timetable_popover.xml",\n',
]
for item in to_remove:
    content = content.replace(item, "")

with open(manifest_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated __manifest__.py successfully")
