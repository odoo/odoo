/** @odoo-module **/

import { Component, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class DevtoolsButtons extends Component {
    static template = "web.DevtoolsButtons";
    setup() {
        this.effect = useService("effect");
        this.buttons = [
            "<h1>Exploring your apps</h1>",
            "<h1>Debugging your code</h1>",
            "<h1>Optimizing your apps</h1>",
        ].map(markup);
    }

    onClick(index) {
        this.effect.add({ message: this.buttons[index], fadeout: "no" });
    }
}

registry.category("systray").add("devtools_buttons", { Component: DevtoolsButtons });
