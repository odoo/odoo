import { BaseHeader } from "@website/interactions/header/base_header";
import { registry } from "@web/core/registry";

const BaseHeaderEdit = I => class extends I {
    adjustPosition() { }
};

registry
    .category("website.editable_active_elements_builders")
    .add("website.base_header", {
        Interaction: BaseHeader,
        mixin: BaseHeaderEdit,
        isAbstract: true,
    });
