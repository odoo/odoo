import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

registry.category("website.form_editor_actions").add('signup_form', {
    formFields: [{
        type: 'name',
        modelRequired: true,
        fillWith: 'name',
        name: 'name',
        string: _t('Name'),
    }, {
        type: 'email',
        modelRequired: true,
        fillWith: 'login',
        name: 'login',
        string: _t('Email'),
    }, {
        type: 'password',
        modelRequired: true,
        fillWith: 'password',
        name: 'password',
        string: _t('Password'),
    }],
});
