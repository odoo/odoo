import { GallerySlider } from "./gallery_slider";
import { registry } from "@web/core/registry";

/**
 * This interaction is kept for compatibility with snippets dropped before 18.0.
 * If you have to update or extend the GallerySlider, you are probably looking
 * for GallerySlider001Edit.
 * @deprecated
 **/
const GallerySliderEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.hideOnClickIndicator = false;
        }
    };

registry.category("public.interactions.edit").add("website.gallery_slider", {
    Interaction: GallerySlider,
    mixin: GallerySliderEdit,
});
