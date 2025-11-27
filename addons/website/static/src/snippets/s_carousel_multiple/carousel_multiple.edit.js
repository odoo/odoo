import { getCarouselCenteringIndex } from "@website/utils/misc";
import { CarouselMultiple } from "./carousel_multiple";
import { registry } from "@web/core/registry";

export const CarouselMultipleEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                ...this.dynamicContent._root,
                "t-on-slide.bs.carousel": this.throttled(this.onSlideCarousel),
            },
            ".s_carousel_multiple_item": {
                "t-on-click": this.onClick,
            },
        };

        onSlideCarousel(event) {
            super.onSlideCarousel(event);
            const displayedSlidesCount = Number(
                getComputedStyle(this.el).getPropertyValue("--o-carousel-multiple-items")
            );
            const itemsLength = this.el.querySelectorAll(".carousel-item").length;
            if (itemsLength <= displayedSlidesCount) {
                return;
            }

            if (event.to >= itemsLength - displayedSlidesCount + 1 && event.direction === "left") {
                // When we are to the last slide and we click to next
                event.preventDefault();
                this.services["website_edit"].applyAction("slideCarousel", {
                    editingElement: this.el,
                    params: {
                        direction: 0,
                        nextTargetElement: this.el,
                    },
                });
            }

            if (event.to === itemsLength - 1 && event.direction === "right") {
                event.preventDefault();
                const targetIndex = itemsLength - displayedSlidesCount;
                this.services["website_edit"].applyAction("slideCarousel", {
                    editingElement: this.el,
                    params: {
                        direction: targetIndex,
                        nextTargetElement: this.el,
                    },
                });
            }
        }

        onResize() {
            const slidesEls = this.el.querySelectorAll(".carousel-item");
            const activeItemEl = this.el.querySelector(".carousel-item.active");
            const activeItemIndex = Array.from(slidesEls).indexOf(activeItemEl);

            // Replicate onResize from carousel_multiple.js but use the website_edit service instead of window.Carousel.
            const currentDisplaySlides = Number(
                getComputedStyle(this.el).getPropertyValue("--o-carousel-multiple-items")
            );
            if (this.env.isSmall) {
                this.carouselInnerEl.removeAttribute("style");
            } else if (currentDisplaySlides !== this.displayedSlidesCount && activeItemIndex != 0) {
                // Reset the slider when the number of displayed slides changes and if we're not in the first slide.
                // The last condition is important to avoid the carousel to freeze in edit mode.
                this.services["website_edit"].applyAction("slideCarousel", {
                    editingElement: this.el,
                    params: { direction: 0 },
                });
            }
            this.displayedSlidesCount = currentDisplaySlides;
        }

        // Center the selected item, if possible.
        onClick(ev) {
            const editingItemEl = ev.currentTarget;
            const carouselCenteringIndex = getCarouselCenteringIndex(editingItemEl);
            // Apply the slide only when the index changes.
            if (carouselCenteringIndex >= 0) {
                this.services["website_edit"].applyAction("slideCarousel", {
                    editingElement: this.el,
                    params: { direction: carouselCenteringIndex, nextTargetElement: editingItemEl },
                });
            }
        }
    };

registry.category("public.interactions.edit").add("website.carousel_multiple_edit", {
    Interaction: CarouselMultiple,
    mixin: CarouselMultipleEdit,
});
