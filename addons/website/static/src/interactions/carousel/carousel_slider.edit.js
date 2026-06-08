import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";
import { patchDynamicContentEntry } from "@web/public/utils";

const CarouselSliderEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                ...this.dynamicContent._root,
                "t-on-content_changed": this.onContentChanged,
                "t-on-focusin": () => {},
                "t-on-focusout": () => {},
            },
        };
        // Pause carousel in edit mode.
        carouselOptions = { ride: false, pause: true, keyboard: false };
        showClickableSlideLinks = false;

        setup() {
            // Do not alter the sliding options behavior in edit mode.
            patchDynamicContentEntry(this.dynamicContent, "_root", "t-att-data-bs-ride", undefined);
            super.setup();
        }

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
