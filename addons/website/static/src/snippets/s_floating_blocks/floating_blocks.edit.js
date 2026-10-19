import { registry } from "@web/core/registry";
import { FloatingBlocks } from "./floating_blocks";

const FloatingBlocksEdit = (I) =>
    class extends I {
        isImpactedBy(el) {
            return (
                this.el.contains(el) &&
                el.matches(".s_floating_blocks_block, .s_floating_blocks_wrapper")
            );
        }
        shouldStop() {
            // The interaction is restarted every time that the content of
            // s_floating_blocks changes. This is needed to provide the correct
            // visual effect when a block is added, removed or moved. This
            // approach is simple, but has the drawback of restarting the
            // interaction also when the content of a block is changed (which is
            // not needed). A more complex approach would be to assign unique
            // IDs to the blocks and check if their order has changed.
            return true;
        }
    };

registry.category("public.interactions.edit").add("website.floating_blocks", {
    Interaction: FloatingBlocks,
    mixin: FloatingBlocksEdit,
});
