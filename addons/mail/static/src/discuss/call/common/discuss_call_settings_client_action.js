import { CallSettings } from "@mail/discuss/call/common/call_settings";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
export class DiscussCallSettingsClientAction extends Component {
    static components = { CallSettings };
    static props = ["*"];
    static template = "mail.DiscussCallSettingsClientAction";
}

registry
    .category("actions")
    .add("mail.discuss_call_settings_action", DiscussCallSettingsClientAction);
