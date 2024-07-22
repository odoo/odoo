/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class Ragbot extends Component {
    static template = "rag_bot.chat";

    static async chat(params) {
        // Action logic here
        console.log("Ragbot chat action triggered", params);
        // Do something with the params, like sending a chat message
    }
}

// registry.category("actions").add("rag_bot.chat", Ragbot);
