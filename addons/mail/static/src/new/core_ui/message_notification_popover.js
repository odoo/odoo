/* @odoo-module */

import { Component } from "@odoo/owl";

export class MessageNotificationPopover extends Component {
    static template = "mail.message_notification_popover";
    static props = ["message", "close?"];
}
