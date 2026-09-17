import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class BlockHoverOverlayEdit extends Interaction {
    static selector =
        ".o_block_hover:is(.o_block_hover_translate, .o_block_hover_zoom_in, .o_block_hover_zoom_out)";
    dynamicContent = {
        _root: {
            "t-on-transitionend": (event) => {
                // The overlay keeps showing the block at rest, as its options
                // apply to it, and as hovering its handles ends the hover
                // effect. Refresh it once back at rest, as it may have been
                // positioned on the moved block, e.g. when selecting it.
                if (
                    event.target === this.el &&
                    event.propertyName === "transform" &&
                    window.getComputedStyle(this.el).transform === "none"
                ) {
                    this.waitForAnimationFrame(this.refreshOverlays);
                }
            },
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
