{
	"name" : "Scrum, Agile Development Method",
	"version": "1.0",
	"author" : "Tiny",
	"depends" : ["project"],
	"category" : "Enterprise Specific Modules/Information Technology",
	"init_xml" : [],
	"description": """
	This modules implements all concepts defined by the scrum project
	management methodology for IT companies:
	* Project with sprints, product owner, scrum master
	* Sprints with reviews, daily meetings, feedbacks
	* Product backlog
	* Sprint backlog

	It adds some concepts to the project management module:
	* Mid-term, long-term roadmaps
	* Customers/functionnal requests, vs technical ones

	It also create a new reporting:
	* Burndown chart

	The scrum projects and tasks inherits from the real projects and
	tasks, so you can continue working on normal tasks that will also
	include tasks from scrum projects.

	More information on the methodology:
	* http://controlchaos.com
	""",
	"demo_xml" : ["scrum_demo.xml"],
	"update_xml": ["scrum_view.xml","scrum_report.xml", "scrum_wizard.xml"],
	"active": False,
	"installable": True
}
