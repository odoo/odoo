import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class CarouselMultiple extends Interaction {
    static selector = ".s_carousel_multiple";

    dynamicContent = {
        _window: { "t-on-resize": this.debounced(this.onResize, 100) },
        _root: {
            "t-on-slid.bs.carousel": this.onSlidCarousel,
        },
        ".carousel-indicators > *": {
            "t-att-aria-label": setAriaLabelOnCarouselMultipleIndicator,
        },
    };

    setup() {
        this.carouselInnerEl = this.el.querySelector(".carousel-inner");
        this.nbItems = this.el.querySelectorAll(".carousel-item").length;
        this.nbDisplayedSlides = Number(
            getComputedStyle(this.el).getPropertyValue("--carousel-multiple-items-per-slide")
        );
        this.carouselInstance = window.Carousel.getOrCreateInstance(this.el);
    }

    destroy() {
        this.carouselInstance.to(0);
        this.el.style.setProperty("--carousel-multiple-current-index", 0);
    }

    onSlidCarousel(event) {
        const lastIndicator = this.nbItems - this.nbDisplayedSlides;
        if (lastIndicator <= 0) {
            return;
        }
        // If we are on the last slide and go to the next one, go to the
        // first one instead.
        if (event.from === lastIndicator && event.to > lastIndicator) {
            this.carouselInstance.to(0);
        }
        // If we are on the first slide and go to the previous one, go to the
        // last one instead.
        if (event.from === 0 && event.to === this.nbItems - 1) {
            this.carouselInstance.to(lastIndicator);
        }
        this.el.style.setProperty("--carousel-multiple-current-index", event.to);
    }

    onResize() {
        const currentDisplaySlides = Number(
            getComputedStyle(this.el).getPropertyValue("--carousel-multiple-items-per-slide")
        );
        if (this.env.isSmall) {
            this.carouselInnerEl.removeAttribute("style");
        } else if (currentDisplaySlides !== this.nbDisplayedSlides) {
            // Reset the slider when the number of displayed slides changes.
            this.carouselInstance.to(0);
            this.el.style.setProperty("--carousel-multiple-current-index", 0);
        }
        this.nbDisplayedSlides = currentDisplaySlides;
    }
}

export function setAriaLabelOnCarouselMultipleIndicator(indicatorEl) {
    const siblingEls = [...indicatorEl.parentElement.children];
    const visibleSiblingEls = siblingEls.filter((el) => getComputedStyle(el).display !== "none");
    return _t("Slide %(itemIndex)s of %(total)s", {
        itemIndex: [...visibleSiblingEls].indexOf(indicatorEl) + 1,
        total: visibleSiblingEls.length,
    });
}

registry.category("public.interactions").add("website.carousel_multiple", CarouselMultiple);
