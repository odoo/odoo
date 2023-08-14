odoo.define('website_sale.form', function (require) {
'use strict';

var FormEditorRegistry = require('website_form.form_editor_registry');

FormEditorRegistry.add('create_customer', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'name',
        string: 'Your Name',
    }, {
        type: 'email',
        required: true,
        name: 'email',
        string: 'Your Email',
    }, {
        type: 'tel',
        name: 'phone',
        string: 'Phone Number',
    }, {
        type: 'char',
        name: 'company_name',
        string: 'Company Name',
    }],
});

});
