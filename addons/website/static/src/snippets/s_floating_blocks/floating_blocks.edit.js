import { FloatingBlocks } from "./floating_blocks";
import { registry } from "@web/core/registry";

const FloatingBlocksEdit = I => class extends I {
    callToAction() {}
};

registry
    .category("public.interactions.edit")
    .add("website.floating_blocks", {
        Interaction: FloatingBlocks,
        mixin: FloatingBlocksEdit,
    });
