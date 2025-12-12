import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { rpc } from "@web/core/network/rpc";

registry.category("website.form_editor_actions").add('apply_job', {
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
        name: 'partner_phone',
        string: _t('Phone Number'),
    }, {
        type: 'char',
        name: 'linkedin_profile',
        string: _t('LinkedIn Profile'),
    }, {
        type: 'text',
        name: 'applicant_notes',
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
        required: true,
        string: _t('Applied Job'),
        dialogTitle: _t('Create a Job position'),
        dialogDescription: _t("Your current changes will be saved and you'll be redirected to a new Job page"),
        noRecordMessage: _t("To create an Application form, You must first create a Job Position."),
        createAction: async() => {
            return await rpc("/jobs/add");
        },
    }, {
        name: 'department_id',
        type: 'many2one',
        relation: 'hr.department',
        string: _t('Department'),
    }],
    successPage: '/job-thank-you',
});
