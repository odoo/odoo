import { _t, translationIsReady } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

translationIsReady.then(() => {
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
    });
});
