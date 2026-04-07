import { Component } from "@odoo/owl";

export class MailingListTemplatePickerSheet extends Component {
    static template = "mass_mailing.MailingListTemplatePickerSheet";
    static props = {
        templates: { type: Object },
        onClick: { type: Function },
    };
}
