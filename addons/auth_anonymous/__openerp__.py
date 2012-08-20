{
 'name': 'Anonymous',
 'description': """
Allow anonymous access to OpenERP.
==================================
 """,
 'author': 'OpenERP SA',
 'version': '1.0',
 'category': 'Authentication',
 'website': 'http://www.openerp.com',
 'installable': True,
 'depends': ['web'],
 'data': [
    'auth_anonymous.xml',
 ],
 'js': [
    'static/src/js/auth_anonymous.js',
 ],
 'qweb': [
     'static/src/xml/auth_anonymous.xml',
 ],
}
