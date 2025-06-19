import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const CarouselSliderEdit = I => class extends I {
    dynamicContent = {
        ...this.dynamicContent,
        _root: {
            ...this.dynamicContent._root,
            "t-on-content_changed": this.onContentChanged,
        },
    };
    // Pause carousel in edit mode.
    carouselOptions = { ride: false, pause: true };

    start() {
        super.start()
        const anchorWrapperEl = this.el.querySelector(".slide-link-wrapper");
        anchorWrapperEl?.classList.remove("z-3");
        anchorWrapperEl?.classList.add("z-n1");
    }

    destroy() {
        const anchorWrapperEl = this.el.querySelector(".slide-link-wrapper");
        anchorWrapperEl?.classList.remove("z-n1");
        anchorWrapperEl?.classList.add("z-3");

    }

    onContentChanged() {
        this.computeMaxHeight();
    }
};

registry
    .category("public.interactions.edit")
    .add("website.carousel_slider", {
        Interaction: CarouselSlider,
        mixin: CarouselSliderEdit,
    });
