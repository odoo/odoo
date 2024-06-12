/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add('apply_job', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'partner_name',
        fillWith: 'name',
        string: _t('Your Name'),
    }, {
        type: 'email',
        required: true,
        fillWith: 'email',
        name: 'email_from',
        string: _t('Your Email'),
    }, {
        type: 'char',
        required: true,
        fillWith: 'phone',
        name: 'partner_mobile',
        string: _t('Phone Number'),
    }, {
        type: 'char',
        name: 'linkedin_profile',
        string: _t('LinkedIn Profile'),
    }, {
        type: 'text',
        name: 'description',
        string: _t('Short Introduction'),
    }, {
        type: 'binary',
        custom: true,
        name: 'Resume',
    }],
    fields: [{
        name: 'job_id',
        type: 'many2one',
        relation: 'hr.job',
        string: _t('Applied Job'),
    }, {
        name: 'department_id',
        type: 'many2one',
        relation: 'hr.department',
        string: _t('Department'),
    }],
    successPage: '/job-thank-you',
});
