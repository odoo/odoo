import { registry } from "@web/core/registry";
import { Interaction } from "./interaction";

class PublicComponentInteraction extends Interaction {
    static selector = "owl-component[name]";

    setup() {
        const name = this.el.getAttribute("name");
        const C = registry.category("public_components").get(name);
        const props = JSON.parse(this.el.getAttribute("props") || "{}");
        // clear owl-component content to make sure we don't have any leftover
        // html from a previous page edit, where owl-components were not properly
        // cleaned up while saving
        this.el.replaceChildren();
        this.mountComponent(this.el, C, props);
    }
}

registry.category("public.interactions").add("public_components", PublicComponentInteraction);
registry.category("public.interactions.edit").add("public_components", {
    Interaction: PublicComponentInteraction,
});
