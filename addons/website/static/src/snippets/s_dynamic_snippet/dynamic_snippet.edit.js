import { registry } from "@web/core/registry";
import { DynamicSnippet } from "./dynamic_snippet";

const DynamicSnippetEdit = I => class extends I {
    /**
     * @override
     */
    callToAction(ev) {}
};

registry
    .category("public.interactions.edit")
    .add("website.dynamic_snippet", {
        Interaction: DynamicSnippet,
        mixin: DynamicSnippetEdit
    });
