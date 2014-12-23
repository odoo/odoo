{
    'name': 'Timeline View',
    'category': 'Hidden',
    'description': """
Timeline view 
==============

    * in progress
""",
    'version': '1.0',
    'depends': ['web', 'base', 'base_setup', 'mail'],
    'data' : [
		"timeline.xml",
		"views/timeline.xml",
	],
	'qweb' : [
		"static/src/xml/timeline.xml",
        "static/src/xml/timeline_followers.xml",
	],
    'auto_install': True
}
