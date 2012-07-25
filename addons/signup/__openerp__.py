{
 'name': 'Signup',
 'description': 'Allow users to sign up',
 'author': 'OpenERP SA',
 'version': '1.0',
 'category': 'Tools',
 'website': 'http://www.openerp.com',
 'installable': True,
 'depends': ['anonymous', 'base_setup'],
 'data': [
    'res_config.xml',
    'signup.xml',
 ],
 'js': [
    'static/src/js/signup.js',
 ],
 'qweb': [
     'static/src/xml/signup.xml',
 ],
}
