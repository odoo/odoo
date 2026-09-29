import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { rpc } from "@web/core/network/rpc";
import { canCreateJobOnCurrentWebsite } from "@website_hr_recruitment/js/systray_items/new_content";

registry.category("builder.form_editor_actions").add('apply_job', {
    fields: [{
        name: 'job_id',
        type: 'many2one',
        relation: 'hr.job',
        required: true,
        string: _t('Applied Job'),
        dialogTitle: _t("Create a Job Position"),
        dialogDescription: _t(
            "Your current changes will be saved, and you'll be redirected to a new Job page."
        ),
        noRecordMessage: _t("To create an application form, you must first create a job position."),
        createAction: () => rpc("/jobs/add"),
        checkWebsiteCompanyIsActive: canCreateJobOnCurrentWebsite,
    }, {
        name: 'department_id',
        type: 'many2one',
        relation: 'hr.department',
        string: _t('Department'),
    }],
    successPage: '/job-thank-you',
});
