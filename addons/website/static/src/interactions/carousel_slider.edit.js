import { registry } from "@web/core/registry";
import { CarouselSlider } from "@website/interactions/carousel_slider";

const CarouselSliderEdit = I => class extends I {
    dynamicContent = Object.assign(this.dynamicContent, {
        _root: {
            "t-on-content_changed": this.onContentChanged,
        },
    });
    // Pause carousel in edit mode.
    carouselOptions = {ride: false, pause: true};

    onContentChanged() {
        this.computeMaxHeight();
    }
};

registry
    .category("public.interactions.edit")
    .add("website.carousel_slider", {
        Interaction: CarouselSlider,
        mixin: CarouselSliderEdit
    });
