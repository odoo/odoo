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
    formFields: [{
        type: 'char',
        custom: true,
        required: true,
        name: 'Your Name',
    }, {
        type: 'char',
        custom: true,
        name: 'Phone Number',
    }, {
        type: 'email',
        modelRequired: true,
        name: 'email_from',
        string: 'Your Email',
    }, {
        type: 'char',
        custom: true,
        name: 'Your Company',
    }, {
        type: 'char',
        modelRequired: true,
        name: 'subject',
        string: 'Subject',
    }, {
        type: 'text',
        custom: true,
        required: true,
        name: 'Your Question',
    }],
    fields: [{
        name: 'email_to',
        type: 'char',
        required: true,
        string: _t('Recipient Email'),
    }],
});

});
