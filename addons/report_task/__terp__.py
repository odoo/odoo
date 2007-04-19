#####################################################################
#Created By 	: Eiffel Consultancy Pvt. Ltd.
#Created Date 	: 14/02/2007
#####################################################################


{
	'name' : 'Report on tasks by user for projects',
	'version' :'1.0',
	'author' : 'Tiny',
	'depends' : ['base','project'],
	'description': 'Gives statistics on tasks by user on projects to check the pipeline of users.',
	'init_xml' : [],
	'update_xml': [
		'report_task_view.xml',
	],
	'active': False,
	'installable': True
}



