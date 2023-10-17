/** @odoo-module **/

import { Component, markup, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class DevtoolsButtons extends Component {
    static template = "web.DevtoolsButtons";
    setup() {
        this.effect = useService("effect");
        this.state = useState({
            1: "<h1>Exploring your apps</h1>",
            2: "<h1>Debugging your code</h1>",
            3: "<h1>Optimizing your apps</h1>",
        });
    }

    onClick(index) {
        this.effect.add({ message: markup(this.state[index]), fadeout: "no" });
    }
}

registry.category("systray").add("devtools_buttons", { Component: DevtoolsButtons });
