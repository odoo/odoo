import { Component } from "@odoo/owl";

export class ReminderPopover extends Component {
    static props = ["close", "message", "onAction", "iconClass"];
    static template = "hr.ReminderPopover";
}
