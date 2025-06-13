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
        super.start();
        this.toggleSlideLinkWrapperClasses();
    }

    destroy() {
        this.toggleSlideLinkWrapperClasses();
    }

    /**
     * Toggles classes on all `.slide-link-wrapper` elements to ensure that
     * slides are not clickable in editing mode to avoid interfering with
     * drag-and-drop or content editing.
     */
    toggleSlideLinkWrapperClasses() {
        const anchorWrapperEls = this.el.querySelectorAll(".slide-link-wrapper");
        anchorWrapperEls?.forEach((anchorWrapperEl) => {
            anchorWrapperEl.classList.toggle("z-3");
            anchorWrapperEl.classList.toggle("z-n1");
        });
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
