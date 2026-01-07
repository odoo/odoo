import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const CarouselSliderEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                ...this.dynamicContent._root,
                // This is what is not working
                "t-on-content_changed": this.onContentChanged,
            },
        };
        // Pause carousel in edit mode.
        carouselOptions = { ride: false, pause: true, keyboard: false };
        showClickableSlideLinks = false;

        start() {
            super.start();

            // Recompute max height when content changes
            const observer = new MutationObserver(() => {
                this.computeMaxHeight();
            });
            observer.observe(this.el, { subtree: true, childList: true });
        }

        onContentChanged() {
            console.log("Content changed - recomputing height");
            this.computeMaxHeight();
        }
    };

registry.category("public.interactions.edit").add("website.carousel_slider", {
    Interaction: CarouselSlider,
    mixin: CarouselSliderEdit,
});
