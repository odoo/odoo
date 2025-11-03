import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const CarouselSliderEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                ...this.dynamicContent._root,
                "t-on-content_changed": this.onContentChanged,
            },
        };
        // Pause carousel in edit mode.
        carouselOptions = { ride: false, pause: true, keyboard: false };
        showClickableSlideLinks = false;

        start() {
            super.start();
            // Monitor carousel size changes to update maxHeight
            const resizeObserver = new ResizeObserver(
                this.debounced(() => {
                    this.computeMaxHeight();
                }, 250)
            );
            resizeObserver.observe(this.el);
            this.registerCleanup(() => resizeObserver.unobserve(this.el));
        }

        onContentChanged() {
            this.computeMaxHeight();
        }
    };

registry.category("public.interactions.edit").add("website.carousel_slider", {
    Interaction: CarouselSlider,
    mixin: CarouselSliderEdit,
});
