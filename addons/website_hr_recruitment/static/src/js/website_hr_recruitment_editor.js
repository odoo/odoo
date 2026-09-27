import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

registry.category("builder.form_editor_actions").add('apply_job', {
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
