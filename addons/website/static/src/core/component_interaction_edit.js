import { registry } from "@web/core/registry";
import { PublicComponentInteraction } from "@web/public/public_component_interaction";

// We register an editable interaction here to add support for <owl-component/>
// in edit mode. The idea is that <owl-components /> in edit mode are rendered,
// but rendered inactive by setting the pointerEvents key to none. To have
// active components in edit mode, one has to register it in the public_components.edit
// registry
const PublicComponentInteractionEdit = (I) =>
    class extends I {
        get Component() {
            const name = this.el.getAttribute("name");
            let C = registry.category("public_components.edit").get(name, false);
            if (!C) {
                C = super.Component;
                // disable <owl-component/> in edit mode
                this.el.style.pointerEvents = "none";
            }
            return C;
        }
    };

registry.category("public.interactions.edit").add("public_components", {
    Interaction: PublicComponentInteraction,
    mixin: PublicComponentInteractionEdit,
});
