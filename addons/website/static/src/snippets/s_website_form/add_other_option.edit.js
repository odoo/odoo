import { registry } from "@web/core/registry";
import { AddOtherOption } from "./add_other_option";

const AddOtherOptionEdit = (I) =>
    class extends I {
        dynamicContent = {
            ".o_other_input": {
                "t-att-class": () => ({ "d-none": false }),
            },
        };

        shouldStop() {
            // Always restart the interaction as some option changes only modify
            // the DOM and do not trigger an automatic restart. Forcing it here
            // ensures interaction-managed elements (e.g., the "Other" input)
            // are correctly re-initialized
            return true;
        }

        start() {
            super.start();
            this.services.website_edit.callShared("builderOverlay", "refreshOverlays");
        }
    };

registry.category("public.interactions.edit").add("website.form.add_other_option", {
    Interaction: AddOtherOption,
    mixin: AddOtherOptionEdit,
});
