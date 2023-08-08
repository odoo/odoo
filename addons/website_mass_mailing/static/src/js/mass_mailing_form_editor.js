/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add('create_mailing_contact', {
    formFields: [{
        name: 'name',
        required: true,
        string: _t('Your Name'),
        type: 'char',
    }, {
        name: 'email',
        required: true,
        string: _t('Your Email'),
        type: 'email',
    }, {
        name: 'list_ids',
        relation: 'mailing.list',
        required: true,
        string: _t('Subscribe to'),
        type: 'many2many',
    }],
});
