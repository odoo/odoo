import { registry } from "@web/core/registry";
import { DynamicSnippet } from "./dynamic_snippet";

const DynamicSnippetEdit = I => class extends I {
    /**
     * @override
     */
    callToAction(ev) {}
};

registry
    .category("website.editable_active_elements_builders")
    .add("website.dynamic_snippet", {
        Interaction: DynamicSnippet,
        mixin: DynamicSnippetEdit
    });
