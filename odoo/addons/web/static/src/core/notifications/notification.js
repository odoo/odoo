/** @odoo-module **/

import { Component } from "@odoo/owl";

export class Notification extends Component {}

Notification.template = "web.NotificationWowl";
Notification.props = {
    message: {
        validate: (m) => {
            return (
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
            );
        },
    },
    title: { type: [String, Boolean, { toString: Function }], optional: true },
    type: {
        type: String,
        optional: true,
        validate: (t) => ["warning", "danger", "success", "info"].includes(t),
    },
    className: { type: String, optional: true },
    buttons: {
        type: Array,
        element: {
            type: Object,
            shape: {
                name: { type: String },
                icon: { type: String, optional: true },
                primary: { type: Boolean, optional: true },
                onClick: Function,
            },
        },
        optional: true,
    },
    close: { type: Function },
    refresh: { type: Function },
    freeze: { type: Function },
};
Notification.defaultProps = {
    buttons: [],
    className: "",
    type: "warning",
};
