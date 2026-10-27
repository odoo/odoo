import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { usePlugin } from "@odoo/owl";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class Tabs extends Interaction {
    static selector = ".s_tabs_common";

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
    }
    start() {
        for (const tabEl of this.el.querySelectorAll("[data-bs-toggle='tab'][role='tab'].active")) {
            this.bootstrap.getOrCreateInstance(window.Tab, tabEl);
        }
    }
}

registry.category("public.interactions").add("website.tabs", Tabs);
