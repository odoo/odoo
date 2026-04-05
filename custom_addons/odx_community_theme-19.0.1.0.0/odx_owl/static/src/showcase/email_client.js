/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ShowcaseEmailClient extends Component {
    static template = "odx_owl.ShowcaseEmailClient";
    static props = { "*": true };
    setup() {
        this.state = useState({
            selectedId: 2,
            composing: false,
            folder: "inbox",
        });
    }
    selectEmail(id) { this.state.selectedId = id; }
    setFolder(f) { this.state.folder = f; }
}

registry.category("actions").add("odx_showcase_email_client", ShowcaseEmailClient);
