/** @odoo-module **/
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

import { Component, useRef } from "@odoo/owl";

class StudioSystray extends Component {
    static template = "web_studio.SystrayItem";
    static props = {};
    setup() {
        this.hm = useService("home_menu");
        this.studio = useService("studio");
        this.rootRef = useRef("root");
        this.isLoading = false;
        this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", () => {
            this.isLoading = true;
            if (this.rootRef.el) {
                this.rootRef.el.classList.toggle("o_disabled", this.buttonDisabled);
            }
        });
        this.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", (ev) => {
            this.isLoading = false;
            const mode = ev.detail;
            if (mode !== "new" && this.rootRef.el) {
                this.rootRef.el.classList.toggle("o_disabled", this.buttonDisabled);
            }
        });
    }
    get buttonDisabled() {
        return this.isLoading || !this.studio.isStudioEditable();
    }
    _onClick() {
        if (!this.isLoading) {
            this.studio.open();
        }
    }
}

export const systrayItem = {
    Component: StudioSystray,
    isDisplayed: () => user.isSystem,
};

registry.category("systray").add("StudioSystrayItem", systrayItem, { sequence: 1 });
