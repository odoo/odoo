import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

registry.category("website.form_editor_actions").add('create_task', {
    formFields: [{
        type: 'char',
        required: true,
        fillWith: 'name',
        name: 'partner_name',
        string: _t('Full Name'),
    }, {
        type: 'tel',
        fillWith: 'phone',
        name: 'partner_phone',
        string: _t('Phone Number'),
    }, {
        type: 'email',
        custom: true,
        required: true,
        fillWith: 'email',
        name: 'email_from',
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
        name: 'project_id',
        type: 'many2one',
        required: true,
        relation: 'project.project',
        string: _t('Project'),
        domain: [["is_template", "=", false]],
        createAction: 'project.open_view_project_all',
    }],
    successPage: '/your-task-has-been-submitted',
});
