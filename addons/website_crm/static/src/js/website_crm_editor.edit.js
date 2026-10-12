import { _t, translationIsReady } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

translationIsReady.then(() => {
    registry.category("website.form_editor_actions").add('create_lead', {
        formFields: [{
            type: 'char',
            required: true,
            name: 'contact_name',
            fillWith: 'name',
            string: _t('Your Name'),
        }, {
            type: 'tel',
            name: 'phone',
            fillWith: 'phone',
            string: _t('Phone Number'),
        }, {
            type: 'email',
            required: true,
            fillWith: 'email',
            name: 'email_from',
            string: _t('Your Email'),
        }, {
            type: 'char',
            name: 'partner_name',
            string: _t('Your Company'),
        }, {
            type: 'char',
            modelRequired: true,
            name: 'name',
            string: _t('Subject'),
        }, {
            type: 'text',
            required: true,
            name: 'description',
            string: _t('Your Question'),
        }],
    });
});
