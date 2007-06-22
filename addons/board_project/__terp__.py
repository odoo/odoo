{
	"name":"Board for project users",
	"version":"1.0",
	"author":"Tiny",
	"category":"Board/Projects & Services",
	"depends":[
		"project",
		"report_timesheet",
		"board",
		"report_analytic_line",
		"report_task",
		"hr_timesheet_sheet"
	],
	"demo_xml":["board_project_demo.xml"],
	"update_xml":["board_project_view.xml", "board_project_manager_view.xml"],
	"description": """
This module implements a dashboard for project member that includes:
	* List of my open tasks
	* List of my next deadlines
	* List of public notes
	* Graph of my timesheet
	* Graph of my work analysis
	""",
	"active":False,
	"installable":True,
}
