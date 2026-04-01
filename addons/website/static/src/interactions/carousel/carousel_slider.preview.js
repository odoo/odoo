import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const CarouselSliderPreview = (I) =>
    class extends I {
        carouselOptions = { ride: true, pause: true, interval: 500 };

        dynamicSelectors = {
            ...this.dynamicSelectors,
            _snippetPreviewWrapEl: () => this.el.closest(".o_snippet_preview_wrap"),
        };
        dynamicContent = {
            ...this.dynamicContent,
            // Bind events to the entire preview wrap. This ensures events
            // trigger when hovering anywhere on the snippet, even though the
            // preview containers are `inert`.
            _snippetPreviewWrapEl: {
                "t-on-mouseenter": this.mouseEnter,
                "t-on-mouseleave": this.mouseLeave,
                "t-on-focusin": this.mouseEnter,
                "t-on-focusout": this.mouseLeave,
            },
        };

        /**
         * Starts the carousel autoplay when the mouse enters the element.
         */
        mouseEnter() {
            const carousel = window.Carousel.getOrCreateInstance(this.el);
            carousel.cycle();
        }

        /**
         * Pauses the carousel and resets it to the first slide when the mouse
         * leaves the element.
         */
        mouseLeave() {
            const carousel = window.Carousel.getOrCreateInstance(this.el);
            carousel.pause();
            carousel.to(0);
        }
    };

registry.category("public.interactions.preview").add("website.carousel_slider", {
    Interaction: CarouselSlider,
    mixin: CarouselSliderPreview,
});
