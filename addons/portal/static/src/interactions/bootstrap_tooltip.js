import { usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class BootstrapTooltip extends Interaction {
    static selector = "[data-bs-toggle='tooltip']";

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
        this.bootstrap.getOrCreateInstance(window.Tooltip, this.el);
    }
}

registry.category("public.interactions").add("website.BootstrapTooltip", BootstrapTooltip);
registry.category("public.interactions.edit").add("website.BootstrapTooltip", {
    Interaction: BootstrapTooltip,
});
