import { registry } from "@web/core/registry";
import { GallerySlider001 } from "@website/snippets/s_image_gallery/gallery_slider_001";

const GallerySlider001Edit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            ".carousel": {
                "t-on-slide.bs.carousel": () => {},
            },
        };
    };

registry.category("public.interactions.edit").add("website.gallery_slider_001", {
    Interaction: GallerySlider001,
    mixin: GallerySlider001Edit,
});
