odoo.define('website_sale.form', function (require) {
'use strict';

var FormEditorRegistry = require('website_form.form_editor_registry');

FormEditorRegistry.add('create_customer', {
    defaultTemplateName: 'website_sale.default_customer_form',
    defaultTemplatePath: '/website_sale/static/src/xml/website_sale_form.xml',
});

});
