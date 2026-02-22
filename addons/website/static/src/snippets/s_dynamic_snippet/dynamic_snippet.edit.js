import { DynamicSnippet } from "./dynamic_snippet";
import { registry } from "@web/core/registry";

const DynamicSnippetEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            ".s_dynamic_snippet_load_more": {
                "t-att-class": () => ({ "d-none": false }),
            },
            ".s_dynamic_snippet_load_more a": {
                "t-on-click": () => {},
            },
        };
        setup() {
            super.setup();
            this.withSample = true;
        }
        callToAction() {}
    };

registry.category("public.interactions.edit").add("website.dynamic_snippet", {
    Interaction: DynamicSnippet,
    mixin: DynamicSnippetEdit,
});
