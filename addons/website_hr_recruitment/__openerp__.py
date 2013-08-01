{
    'name': 'Career Form',
    'category': '',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'hr', 'hr_recruitment'],
    'data': [
        'views/website_hr_recruitment.xml'
    ],
    'js':[
          'static/src/js/*.js',
      ],
    'css':[
       'static/src/css/*.css'
      ],
    'installable': True,
    'auto_install': False,
}
