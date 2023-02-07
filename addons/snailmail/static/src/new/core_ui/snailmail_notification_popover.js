/* @odoo-module */

import { Component } from "@odoo/owl";

export class SnailmailNotificationPopover extends Component {
    static template = "snailmail.snailmail_notification_popover";
    static props = ["message", "close?"];
}
