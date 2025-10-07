import { CarouselMultiple } from "./carousel_multiple";
import { registry } from "@web/core/registry";

const CarouselMultipleEdit = (I) => class extends I {
    onResize() {
        const slidesEls = this.el.querySelectorAll('.carousel-item');
        const activeItemEl = this.el.querySelector('.carousel-item.active');
        const activeItemIndex = Array.from(slidesEls).indexOf(activeItemEl);

        // Replicate onResize from carousel_multiple.js but use the website_edit service instead of window.Carousel.
        const currentDisplaySlides = Number(getComputedStyle(this.el).getPropertyValue("--o-carousel-multiple-items"));
        if(this.env.isSmall) {
            this.carouselInnerEl.removeAttribute('style');
        } else if (currentDisplaySlides !== this.displayedSlidesCount && activeItemIndex != 0) {
            // Reset the slider when the number of displayed slides changes and if we're not in the first slide.
            // The last condition is important to avoid the carousel to freeze in edit mode.
            this.services["website_edit"].applyAction("slideCarousel", { editingElement: this.el, params: { direction: 0 } });
        }
        this.displayedSlidesCount = currentDisplaySlides;
    }

    // Center the selected item, if possible.
    onClick(ev) {
        const editingItemEl = ev.target.closest('.carousel-item');

        // If we click inside a carousel-item
        // TODO: when clicking on indicators and arrows, it's considered as clicking inside a
        // carousel-item, which creates a buggy behavior when sliding.
        if (editingItemEl && editingItemEl.contains(ev.target)) {
            const carouselEl = ev.target.closest('.carousel');
            const slidesEls = carouselEl.querySelectorAll('.carousel-item');
            const editingItemIndex = Array.from(slidesEls).indexOf(editingItemEl);
            const activeItemEl = carouselEl.querySelector('.carousel-item.active');
            const activeItemIndex = Array.from(slidesEls).indexOf(activeItemEl);
            const currentDisplaySlides = Number(getComputedStyle(carouselEl).getPropertyValue("--o-carousel-multiple-items"));
            const maxSteps = slidesEls.length - currentDisplaySlides;
            const centerEditingItemIndex = Math.min(Math.max(editingItemIndex - Math.floor(currentDisplaySlides / 2), 0), maxSteps);

            // Apply the slide only when the index changes.
            if (activeItemIndex !== centerEditingItemIndex) {
                this.services["website_edit"].applyAction("slideCarousel", { editingElement: this.el, params: { direction: centerEditingItemIndex } });
            }
        }
    }
};

registry
    .category("public.interactions.edit")
    .add("website.carousel_multiple", {
        Interaction: CarouselMultiple,
        mixin: CarouselMultipleEdit,
    });
