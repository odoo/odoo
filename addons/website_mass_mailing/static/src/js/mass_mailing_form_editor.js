import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

registry.category("website.form_editor_actions").add('create_mailing_contact', {
    formFields: [{
        name: 'name',
        required: true,
        fillWith: "name",
        string: _t('Your Name'),
        type: 'char',
    }, {
        name: 'email',
        modelRequired: true,
        fillWith: "email",
        string: _t('Your Email'),
        type: 'email',
    }, {
        name: 'list_ids',
        relation: 'mailing.list',
        modelRequired: true,
        string: _t('Subscribe to'),
        type: 'many2many',
    }],
});
