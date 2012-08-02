{
 'name': 'Reset Password',
 'description': 'Allow users to reset their password from the login page',
 'author': 'OpenERP SA',
 'version': '1.0',
 'category': 'Authentication',
 'website': 'http://www.openerp.com',
 'installable': True,
 'depends': ['auth_anonymous', 'email_template'],
 'data': [
     'auth_reset_password.xml',
 ],
 'js': [
     'static/src/js/reset_password.js',
 ],
 'css': [
     'static/src/css/reset_password.css',
 ],
 'qweb': [
     'static/src/xml/reset_password.xml',
 ],
}
