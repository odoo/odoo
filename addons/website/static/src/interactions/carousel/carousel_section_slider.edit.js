import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { patchDynamicContentEntry } from "@web/public/utils";

const CAROUSEL_CONTROLLERS_SELECTOR = ".carousel-control-prev, .carousel-control-next";
const CAROUSEL_INDICATORS_SELECTOR = ".carousel-indicators > *";
export class CarouselSectionSliderEdit extends Interaction {
    static selector = "section > .carousel";
    dynamicContent = {
        [CAROUSEL_CONTROLLERS_SELECTOR]: {
            "t-att-data-bs-slide": () => undefined,
            "t-on-mousedown": this.onControlClick,
        },
        [CAROUSEL_INDICATORS_SELECTOR]: {
            "t-att-data-bs-slide-to": () => undefined,
            "t-on-mousedown": this.onControlClick,
        },
    };

    setup() {
        // Enable carousel sliding in translation mode to allow access to
        // all slides for translation.
        // Otherwise, only the first slide would be translatable.
        if (this.services.website_edit.isEditingTranslations()) {
            patchDynamicContentEntry(
                this.dynamicContent,
                CAROUSEL_CONTROLLERS_SELECTOR,
                "t-att-data-bs-slide",
                undefined
            );
            patchDynamicContentEntry(
                this.dynamicContent,
                CAROUSEL_INDICATORS_SELECTOR,
                "t-att-data-bs-slide-to",
                undefined
            );
        }
    }
    destroy() {
        const editTranslations = this.services.website_edit.isEditingTranslations();
        if (!editTranslations) {
            // Restore the carousel controls.
            const indicatorEls = this.el.querySelectorAll(".carousel-indicators > *");
            indicatorEls.forEach((indicatorEl, i) => indicatorEl.setAttribute("data-bs-slide-to", i));
        }
    }

    /**
     * Redirects a carousel control click on the active slide.
     */
    onControlClick() {
        this.el.querySelector(".carousel-item.active").click();
    }
}

registry
    .category("public.interactions.edit")
    .add("website.carousel_section_slider", {
        Interaction: CarouselSectionSliderEdit,
    });
