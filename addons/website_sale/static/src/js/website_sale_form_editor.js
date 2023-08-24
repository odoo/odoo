/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import FormEditorRegistry from "website.form_editor_registry";

FormEditorRegistry.add('create_customer', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'name',
        fillWith: 'name',
        string: _lt('Your Name'),
    }, {
        type: 'email',
        required: true,
        fillWith: 'email',
        name: 'email',
        string: _lt('Your Email'),
    }, {
        type: 'tel',
        fillWith: 'phone',
        name: 'phone',
        string: _lt('Phone Number'),
    }, {
        type: 'char',
        name: 'company_name',
        fillWith: 'commercial_company_name',
        string: _lt('Company Name'),
    }],
});
