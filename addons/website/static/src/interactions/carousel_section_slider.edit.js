import { registry } from "@web/core/registry";
import { Interaction } from "@website/core/interaction";

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

    // TODO See if slide indices need to be re-generated or is restore
    // sufficient.
    /*
    destroy() {
        super.destroy();
        /*
        if (this.editableMode && this.el.matches("section > .carousel")) {
            // TODO Handle translation mode.
//                && !this.options.wysiwyg.options.enableTranslation) {
            // Restore the carousel controls.
            const indicatorEls = this.el.querySelectorAll(".carousel-indicators > *");
            this.options.wysiwyg.odooEditor.observerUnactive("restore_controls");
            indicatorEls.forEach((indicatorEl, i) => indicatorEl.setAttribute("data-bs-slide-to", i));
            this.options.wysiwyg.odooEditor.observerActive("restore_controls");
        }
    }
    */

    /**
     * Redirects a carousel control click on the active slide.
     */
    onControlClick() {
        this.el.querySelector(".carousel-item.active").click();
    }
}

registry
    .category("website.editable_active_elements_builders")
    .add("website.carousel_section_slider", {
        Interaction: CarouselSectionSliderEdit,
    });
