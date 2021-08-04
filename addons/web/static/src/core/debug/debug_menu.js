/** @odoo-module **/

import { useEnvDebugContext } from "./debug_context";

const { Component } = owl;

export class DebugMenu extends Component {
    setup() {
        const debugContext = useEnvDebugContext();
        // Needs to be bound to this for use in template
        this.getElements = async () => {
            this.elements = await debugContext.getItems(this.env);
        };
    }
}
DebugMenu.template = "web.DebugMenu";
