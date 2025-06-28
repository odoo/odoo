/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add('send_mail', {
    formFields: [{
        type: 'char',
        custom: true,
        required: true,
        fillWith: 'name',
        name: 'name',
        string: _t('Your Name'),
    }, {
        type: 'tel',
        custom: true,
        fillWith: 'phone',
        name: 'phone',
        string: _t('Phone Number'),
    }, {
        type: 'email',
        modelRequired: true,
        fillWith: 'email',
        name: 'email_from',
        string: _t('Your Email'),
    }, {
        type: 'char',
        custom: true,
        fillWith: 'commercial_company_name',
        name: 'company',
        string: _t('Your Company'),
    }, {
        type: 'char',
        modelRequired: true,
        name: 'subject',
        string: _t('Subject'),
    }, {
        type: 'text',
        custom: true,
        required: true,
        name: 'description',
        string: _t('Your Question'),
    }],
    fields: [{
        name: 'email_to',
        type: 'char',
        required: true,
        string: _t('Recipient Email'),
        defaultValue: 'info@yourcompany.example.com',
    }],
});
