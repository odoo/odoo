/** @odoo-module **/

import core from "web.core";
import FormEditorRegistry from "website.form_editor_registry";

const _lt = core._lt;

FormEditorRegistry.add('create_mailing_contact', {
    formFields: [{
        name: 'name',
        required: true,
        string: _lt('Your Name'),
        type: 'char',
    }, {
        name: 'email',
        required: true,
        string: _lt('Your Email'),
        type: 'email',
    }, {
        name: 'list_ids',
        relation: 'mailing.list',
        required: true,
        string: _lt('Subscribe to'),
        type: 'many2many',
    }],
});
