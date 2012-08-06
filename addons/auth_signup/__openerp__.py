{
 'name': 'Signup',
 'description': 'Allow users to sign up',
 'author': 'OpenERP SA',
 'version': '1.0',
 'category': 'Authentication',
 'website': 'http://www.openerp.com',
 'installable': True,
 'depends': ['auth_anonymous', 'base_setup'],
 'data': [
     'auth_signup.xml',
     'res_config.xml',
 ],
 'js': [
     'static/src/js/auth_signup.js',
 ],
 'css': [
     'static/src/css/auth_signup.css',
 ],
 'qweb': [
     'static/src/xml/auth_signup.xml',
 ],
}
