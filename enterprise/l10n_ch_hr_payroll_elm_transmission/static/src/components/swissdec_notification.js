/** @odoo-module **/
import {Component} from "@odoo/owl";

export class SwissdecNotification extends Component {
    static template = "swissdec_notification_template";
    static props = {
        type: { type: String },
        notifications: { type: Array }
    };
}

export default SwissdecNotification;
