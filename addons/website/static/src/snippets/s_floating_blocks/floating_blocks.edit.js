import { registry } from "@web/core/registry";
import { FloatingBlocks } from "./floating_blocks";

const FloatingBlocksEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            ".s_floating_blocks_alert_empty": {
                "t-on-click": this.onAddCard.bind(this),
            },
        };
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
        start() {
            // The "No card" message must be injected *before* the removal of
            // the last block, otherwise the snippet could be automatically
            // removed by the editor during edition:
            // see remove_plugin.isEmptyAndRemovable()
            this.renderAt(
                "website.s_floating_blocks.alert.empty",
                {},
                this.el.querySelector(".s_floating_blocks_wrapper")
            );
            super.start();
        }
        onAddCard() {
            const applySpec = { editingElement: this.el };
            this.services["website_edit"].applyAction("addFloatingBlockCard", applySpec);
        }
    };

registry.category("public.interactions.edit").add("website.floating_blocks", {
    Interaction: FloatingBlocks,
    mixin: FloatingBlocksEdit,
});
