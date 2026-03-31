import { Component } from "@odoo/owl";

export class MailingListTypePickerSheet extends Component {
    static template = "mass_mailing.MailingListTypePickerSheet";
    static props = {
        listTypes: { type: Object },
        onClick: { type: Function },
    };
}
