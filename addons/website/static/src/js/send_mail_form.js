/** @odoo-module **/

import core from "web.core";
import FormEditorRegistry from "website.form_editor_registry";

var _t = core._t;

FormEditorRegistry.add('send_mail', {
    formFields: [{
        type: 'char',
        custom: true,
        required: true,
        fillWith: 'name',
        name: 'name',
        string: 'Your Name',
    }, {
        type: 'tel',
        custom: true,
        fillWith: 'phone',
        name: 'phone',
        string: 'Phone Number',
    }, {
        type: 'email',
        modelRequired: true,
        fillWith: 'email',
        name: 'email_from',
        string: 'Your Email',
    }, {
        type: 'char',
        custom: true,
        fillWith: 'commercial_company_name',
        name: 'company',
        string: 'Your Company',
    }, {
        type: 'char',
        modelRequired: true,
        name: 'subject',
        string: 'Subject',
    }, {
        type: 'text',
        custom: true,
        required: true,
        name: 'description',
        string: 'Your Question',
    }],
    fields: [{
        name: 'email_to',
        type: 'char',
        required: true,
        string: _t('Recipient Email'),
        defaultValue: 'info@yourcompany.example.com',
    }],
});
