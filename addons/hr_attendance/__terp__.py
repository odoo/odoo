{
    "name" : "Attendances Of Employees",
    "version" : "1.0",
    "author" : "Tiny",
    "category" : "Generic Modules/Human Resources",
    "description": "This module aims to manage employee's attendances.",
    "depends" : ["base","hr",],
    "demo_xml" : ["hr_attendance_demo.xml"],
    "update_xml" : [
       "hr_attendance_view.xml",
       "hr_attendance_wizard.xml",
       "hr_attendance_report.xml",
	   "security/ir.model.access.csv",
    ],
    "active": False,
    "installable": True,
}
