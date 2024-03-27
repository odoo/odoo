import { Component } from "@odoo/owl";
import { DiscussCallSettings } from "@mail/discuss/core/common/discuss_call_settings";

import { registry } from "@web/core/registry";

export class DiscussCallSettingsClientAction extends Component {
    static components = { DiscussCallSettings };
    static props = ["*"];
    static template = "discuss.CallSettingsClientAction";
}

registry.category("actions").add("discuss.call_settings_action", DiscussCallSettingsClientAction);
