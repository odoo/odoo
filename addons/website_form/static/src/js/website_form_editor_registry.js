odoo.define('website_form.form_editor_registry', function (require) {
'use strict';

var Registry = require('web.Registry');

return new Registry();

});

odoo.define('website_form.send_mail_form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website_form.form_editor_registry');

var _t = core._t;

FormEditorRegistry.add('send_mail', {
    defaultTemplateName: 'website_form.default_contactus_form',
    defaultTemplatePath: '/website_form/static/src/xml/website_form.xml',
    fields: [{
        name: 'email_to',
        type: 'char',
        required: true,
        string: _t('Recipient Email'),
    }],
});

});
