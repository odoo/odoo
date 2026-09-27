import { registry } from "@web/core/registry";
import { Interaction } from "./interaction";

export class PublicComponentInteraction extends Interaction {
    static selector = "owl-component[name]";

    setup() {
        const props = JSON.parse(this.el.getAttribute("props") || "{}");
        // clear owl-component content to make sure we don't have any leftover
        // html from a previous page edit, where owl-components were not properly
        // cleaned up while saving
        this.el.replaceChildren();
        this.mountComponent(this.el, this.Component, props);
    }

    get Component() {
        const name = this.el.getAttribute("name");
        return registry.category("public_components").get(name);
    }
}

registry.category("public.interactions").add("public_components", PublicComponentInteraction);
