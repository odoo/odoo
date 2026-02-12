import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const ANIM_REFRESH_OVERLAY =
    ".o_anim_hover_translate, .o_anim_hover_zoom_in, .o_anim_hover_zoom_out";

// This interaction is used to update the Overlay that would be misplaced
// because of an translate / zoom animation.
export class AnimationHoverEdit extends Interaction {
    static selector = ANIM_REFRESH_OVERLAY;
    dynamicContent = {
        _root: {
            "t-on-pointerleave": this.debounced(this.refreshOverlays, 300),
        },
    };

    setup() {
        this.websiteEditService = this.services.website_edit;
    }

    refreshOverlays() {
        this.websiteEditService.callShared("builderOverlay", "refreshOverlays");
    }
}

registry.category("public.interactions.edit").add("website.animation_hover_edit", {
    Interaction: AnimationHoverEdit,
});
