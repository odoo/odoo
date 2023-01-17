/** @odoo-module **/

import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";
import { registry } from "@web/core/registry";

/**
 * Select an email provider.
 */
export class SelectionMailProviderField extends SelectionField {
    static template = "mail.SelectionMailProviderField";

    getIcon(option) {
        if (option.includes("gmail")) {
            return "/mail/static/src/img/providers/gmail.svg";
        } else if (option.includes("outlook")) {
            return "/mail/static/src/img/providers/outlook.svg";
        } else if (option.includes("mailjet")) {
            return "/mail/static/src/img/providers/mailjet.svg";
        } else if (option.includes("gmx")) {
            return "/mail/static/src/img/providers/gmx.png";
        }
        return "/web/static/img/placeholder.png";
    }
}

export const mailProviderSelection = {
    ...selectionField,
    component: SelectionMailProviderField,
};

registry.category("fields").add("selection_mail_provider", mailProviderSelection);
