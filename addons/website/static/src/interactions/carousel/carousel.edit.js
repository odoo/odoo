import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CarouselEdit extends Interaction {
    static selector = "section > .carousel";
    // Prevent enabling the carousel overlay when clicking on the carousel
    // controls (indeed we want it to change the carousel slide then enable
    // the slide overlay) + See "CarouselItem" option.
    dynamicContent = {
        ".carousel-control-prev, .carousel-control-next, .carousel-indicators": {
            "t-on-click": this.throttled(this.onControlClick),
            "t-att-class": () => ({ o_we_no_overlay: true }),
        },
        ".carousel-control-prev, .carousel-control-next": {
            "t-att-data-bs-slide": () => undefined,
        },
        ".carousel-indicators > *": {
            "t-att-data-bs-slide-to": () => undefined,
        },
    };

    /**
     * Slides the carousel when clicking on the carousel controls. This handler
     * allows to put the sliding in the mutex, to avoid race conditions.
     *
     * @param {Event} ev
     */
    async onControlClick(ev) {
        // Activate the active slide.
        this.el.querySelector(".carousel-item.active").click();

        // Compute to which slide the carousel will slide.
        const controlEl = ev.currentTarget;
        let direction;
        if (controlEl.classList.contains("carousel-control-prev")) {
            direction = "prev";
        } else if (controlEl.classList.contains("carousel-control-next")) {
            direction = "next";
        } else {
            const indicatorEl = ev.target;
            if (
                !indicatorEl.matches(".carousel-indicators > *") ||
                indicatorEl.classList.contains("active")
            ) {
                return;
            }
            direction = [...controlEl.children].indexOf(indicatorEl);
        }

        // Slide the carousel
        const applySpec = { editingElement: this.el, params: { direction: direction } };

        if (this.services["website_edit"].applyAction) {
            this.services["website_edit"].applyAction("slideCarousel", applySpec);
        }
    }

    destroy() {
        const editTranslations = this.services.website_edit.isEditingTranslations();
        if (!editTranslations) {
            // Restore the carousel controls.
            const indicatorEls = this.el.querySelectorAll(".carousel-indicators > *");
            indicatorEls.forEach((indicatorEl, i) =>
                indicatorEl.setAttribute("data-bs-slide-to", i)
            );
        }
    }
}

registry.category("public.interactions.edit").add("website.carousel_edit", {
    Interaction: CarouselEdit,
});
