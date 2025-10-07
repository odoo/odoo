import { registry } from "@web/core/registry";
import { CarouselEdit } from "@website/interactions/carousel/carousel.edit";
import { setAriaLabelOnCarouselMultipleIndicator } from "./carousel_multiple";

export class CarouselMultipleEdit extends CarouselEdit {
    static selector = ".s_carousel_multiple";

    dynamicContent = {
        ...this.dynamicContent,
        _root: {
            "t-on-keydown.capture": (ev) => {
                if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
                    ev.stopPropagation();
                }
            },
        },
        ".carousel-indicators > *": {
            ...this.dynamicContent[".carousel-indicators > *"],
            "t-att-aria-label": setAriaLabelOnCarouselMultipleIndicator,
        },
    };

    onControlClick(ev) {
        const nbItems = this.el.querySelectorAll(".carousel-item").length;
        const nbDisplayedSlides = Number(
            getComputedStyle(this.el).getPropertyValue("--carousel-multiple-items-per-slide")
        );
        const maxIndicator = nbItems - nbDisplayedSlides;

        const indicatorEls = [...this.el.querySelectorAll(".carousel-indicators > *")];
        const activeIndicatorEl = this.el.querySelector(".carousel-indicators > .active");
        const activeIndex = indicatorEls.indexOf(activeIndicatorEl);

        // Compute to which slide the carousel will slide.
        const controlEl = ev.currentTarget;
        let direction;
        if (controlEl.classList.contains("carousel-control-prev")) {
            direction = activeIndex === 0 ? maxIndicator : activeIndex - 1;
        } else if (controlEl.classList.contains("carousel-control-next")) {
            direction = activeIndex === maxIndicator ? 0 : activeIndex + 1;
        } else {
            const indicatorEl = ev.target;
            if (
                !indicatorEl.matches(".carousel-indicators > *") ||
                indicatorEl.classList.contains("active")
            ) {
                return;
            }
            direction = indicatorEls.indexOf(indicatorEl);
        }

        // Slide the carousel
        if (this.services["website_edit"].applyAction) {
            const applySpec = { editingElement: this.el, params: { direction: direction } };
            this.services["website_edit"].applyAction("slideCarouselMultiple", applySpec);
        }
    }
}

registry.category("public.interactions.edit").add("website.carousel_multiple_edit", {
    Interaction: CarouselMultipleEdit,
});
