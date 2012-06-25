{
 'name': 'Signup',
 'description': 'Allow users to register',
 'author': 'OpenERP SA',
 'version': '1.0',
 'category': 'Tools',
 'website': 'http://www.openerp.com',
 'installable': True,
 'depends': ['anonymous', 'base_setup'],
 'data': [
    'signup_wizard.xml',
    'res_config.xml',
 ],
 'js': [
    'static/src/js/signup.js',
 ],
 #'css': [
 #    'static/src/css/reset_password.css',
 #],
 'qweb': [
     'static/src/xml/signup.xml',
 ],
}
