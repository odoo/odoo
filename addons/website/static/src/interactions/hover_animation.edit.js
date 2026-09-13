import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class BlockHoverOverlayEdit extends Interaction {
    static selector =
        ".o_block_hover:is(.o_block_hover_translate, .o_block_hover_zoom_in, .o_block_hover_zoom_out)";
    dynamicContent = {
        _root: {
            // Hover effects can move or resize the block, leaving the builder
            // overlay out of sync once the pointer leaves. Wait for the CSS
            // transition to settle before refreshing overlay geometry.
            "t-on-pointerleave": this.debounced(
                () => this.waitForAnimationFrame(this.refreshOverlays),
                350
            ),
        },
    };

    setup() {
        this.websiteEditService = this.services.website_edit;
    }

    refreshOverlays() {
        this.websiteEditService.callShared("builderOverlay", "refreshOverlays");
    }
}

registry.category("public.interactions.edit").add("website.block_hover_overlay_edit", {
    Interaction: BlockHoverOverlayEdit,
});
