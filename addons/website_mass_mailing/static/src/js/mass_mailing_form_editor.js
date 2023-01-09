/** @odoo-module **/

import core from "web.core";
import FormEditorRegistry from "website.form_editor_registry";

const _t = core._t;

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
