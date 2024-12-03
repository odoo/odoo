import { registry } from "@web/core/registry";
import { CarouselSlider } from "@website/interactions/carousel_slider";

export class CarouselSliderEdit extends CarouselSlider {
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
}

registry
    .category("website.edit_active_elements")
    .add("website.carousel_slider", CarouselSliderEdit);
