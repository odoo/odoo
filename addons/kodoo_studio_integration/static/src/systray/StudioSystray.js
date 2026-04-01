/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component } from "@odoo/owl";

export class StudioSystray extends Component {
    static template = "kodoo_studio_integration.StudioSystray";
    static props = {};

    setup() {
        this.action = useService("action");
    }

    openStudio() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "kodoo_studio",
            target: "main",
        });
    }
}

registry.category("systray").add(
    "kodoo_studio_integration.StudioSystray",
    {
        Component: StudioSystray,
        isDisplayed: () => user.isSystem,
    },
    { sequence: 1 }
);
