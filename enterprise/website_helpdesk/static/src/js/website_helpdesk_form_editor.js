/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add('create_ticket', {
    formFields: [{
        type: 'char',
        required: true,
        name: 'partner_name',
        fillWith: 'name',
        string: _t('Full Name'),
    }, {
        type: 'tel',
        name: 'partner_phone',
        fillWith: 'phone',
        string: _t('Phone Number'),
    }, {
        type: 'email',
        required: true,
        name: 'partner_email',
        fillWith: 'email',
        string: _t('Email Address'),
    }, {
        type: 'char',
        fillWith: 'commercial_company_name',
        name: 'partner_company_name',
        string: _t('Company Name'),
    }, {
        type: 'char',
        modelRequired: true,
        name: 'name',
        string: _t('Message Subject'),
    }, {
        type: 'text',
        required: true,
        name: 'description',
        string: _t('Ask Your Question'),
    }, {
        type: 'binary',
        custom: true,
        name: _t('Attach File'),
    }],
    fields: [{
        name: 'team_id',
        type: 'many2one',
        relation: 'helpdesk.team',
        string: _t('Helpdesk Team'),
    }],
    successPage: '/your-ticket-has-been-submitted',
});
