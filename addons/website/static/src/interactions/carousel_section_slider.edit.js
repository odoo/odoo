import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class CarouselSectionSliderEdit extends Interaction {
    static selector = "section > .carousel";
    dynamicContent = {
        ".carousel-control-prev, .carousel-control-next": {
            "t-att-data-bs-slide": () => undefined,
            "t-on-mousedown": this.onControlClick,
        },
        ".carousel-indicators > *": {
            "t-att-data-bs-slide-to": () => undefined,
            "t-on-mousedown": this.onControlClick,
        },
    };

    destroy() {
        const editTranslations = this.services.website_edit.isEditingTranslations();
        if (!editTranslations) {
            // Restore the carousel controls.
            const indicatorEls = this.el.querySelectorAll(".carousel-indicators > *");
            // this.options.wysiwyg.odooEditor.observerUnactive("restore_controls");
            indicatorEls.forEach((indicatorEl, i) => indicatorEl.setAttribute("data-bs-slide-to", i));
            // this.options.wysiwyg.odooEditor.observerActive("restore_controls");
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
