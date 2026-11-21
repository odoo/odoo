with open("custom/school_management/__manifest__.py", "r", encoding="utf-8") as f:
    c = f.read()

dep_target = """    "depends": [
        "auth_signup",
        "base",
        "mail",
        "portal",
        "web",
    ],"""

dep_replacement = """    "depends": [
        "auth_signup",
        "base",
        "mail",
        "portal",
        "web",
        "spreadsheet_dashboard",
    ],"""

assert dep_target in c
c = c.replace(dep_target, dep_replacement, 1)

data_target = '"data/timetable_config_param.xml",'
data_replacement = '"data/timetable_config_param.xml",\n        "data/academic_spreadsheet_dashboard.xml",'

assert data_target in c
c = c.replace(data_target, data_replacement, 1)

with open("custom/school_management/__manifest__.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Updated custom/school_management/__manifest__.py successfully!")
