/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";

export class MailActivityType extends models.ServerModel {
    _name = "mail.activity.type";

    _records = [
        {
            id: 1,
            icon: "fa-envelope",
            name: "Email",
        },
        {
            id: 2,
            category: "phonecall",
            icon: "fa-phone",
            name: "Call",
        },
        {
            id: 28,
            icon: "fa-upload",
            name: "Upload Document",
        },
    ];
}
