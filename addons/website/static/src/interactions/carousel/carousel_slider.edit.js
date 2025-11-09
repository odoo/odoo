import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const quoteCarouselInnerSelector =
    "section[data-snippet='s_quotes_carousel'] .carousel-inner, section[data-snippet='s_quotes_carousel_minimal'] .carousel-inner";

const CarouselSliderEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                ...this.dynamicContent._root,
                "t-on-content_changed": this.onContentChanged,
            },
            [quoteCarouselInnerSelector]: {
                "t-on-click": this.onClick,
                "t-on-slide.bs.carousel": this.onSlideCarousel,
                "t-on-slid.bs.carousel": this.onSlidCarousel,
            },
        };
        // Pause carousel in edit mode.
        carouselOptions = { ride: false, pause: true, keyboard: false };
        showClickableSlideLinks = false;

        onContentChanged() {
            this.computeMaxHeight();
        }
        removeFocusedSlideClass() {
            this.carouselInnerEl
                .querySelector(".o-focused-slide")
                ?.classList.remove("o-focused-slide");
        }
        onClick(event) {
            this.removeFocusedSlideClass();
            event.target.closest(".carousel-slide")?.classList.add("o-focused-slide");
        }
        onSlideCarousel(ev) {
            this.removeFocusedSlideClass();
            super.onSlideCarousel(ev);
        }
        onSlidCarousel(event) {
            super.onSlidCarousel(event);
            event.relatedTarget.classList.add("o-focused-slide");
        }
    };

registry.category("public.interactions.edit").add("website.carousel_slider", {
    Interaction: CarouselSlider,
    mixin: CarouselSliderEdit,
});
