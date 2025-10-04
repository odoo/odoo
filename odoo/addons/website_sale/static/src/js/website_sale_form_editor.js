/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add('create_customer', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'name',
        fillWith: 'name',
        string: _t('Your Name'),
    }, {
        type: 'email',
        required: true,
        fillWith: 'email',
        name: 'email',
        string: _t('Your Email'),
    }, {
        type: 'tel',
        fillWith: 'phone',
        name: 'phone',
        string: _t('Phone Number'),
    }, {
        type: 'char',
        name: 'company_name',
        fillWith: 'commercial_company_name',
        string: _t('Company Name'),
    }],
});
