/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ShowcaseChatApp extends Component {
    static template = "odx_owl.ShowcaseChatApp";
    static props = { "*": true };
    setup() {
        this.state = useState({ activeChannel: "general" });
    }
    setChannel(ch) { this.state.activeChannel = ch; }
}

registry.category("actions").add("odx_showcase_chat_app", ShowcaseChatApp);
