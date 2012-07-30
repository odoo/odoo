{
 'name': 'Anonymous',
 'description': 'Allow anonymous access to OpenERP.',
 'author': 'OpenERP SA',
 'version': '1.0',
 'category': 'Tools',
 'website': 'http://www.openerp.com',
 'installable': True,
 'depends': ['web'],
 'data': [
    'anonymous.xml',
 ],
 'js': [
    'static/src/js/anonymous.js',
 ],
 'qweb': [
     'static/src/xml/anonymous.xml',
 ],
}
