import { BaseHeader } from "@website/interactions/header/base_header";
import { registry } from "@web/core/registry";

const BaseHeaderEdit = I => class extends I {
    adjustPosition() { }
};

registry
    .category("public.interactions.edit")
    .add("website.base_header", {
        Interaction: BaseHeader,
        mixin: BaseHeaderEdit,
        isAbstract: true,
    });
