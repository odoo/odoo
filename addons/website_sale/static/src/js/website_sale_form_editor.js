odoo.define('website_sale.form', function (require) {
'use strict';

var FormEditorRegistry = require('website.form_editor_registry');

FormEditorRegistry.add('create_customer', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'name',
        fillWith: 'name',
        string: 'Your Name',
    }, {
        type: 'email',
        required: true,
        fillWith: 'email',
        name: 'email',
        string: 'Your Email',
    }, {
        type: 'tel',
        fillWith: 'phone',
        name: 'phone',
        string: 'Phone Number',
    }, {
        type: 'char',
        name: 'company_name',
        fillWith: 'commercial_company_name',
        string: 'Company Name',
    }],
});

});
