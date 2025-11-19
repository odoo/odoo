import { registry } from "@web/core/registry";
import { CarouselMultiple } from "./carousel_multiple";

// When the interaction starts, we clone the carousel items and append them to
// both ends of the carousel. When we slide we try to normalize indexes to
// show always only the original items. This creates an infinite loop effect,
// allowing the user to scroll indefinitely without reaching the end.
export class CarouselMultipleInfiniteSliding extends CarouselMultiple {
    static selector = ".s_carousel_multiple[data-infinite-sliding='true']";

    dynamicContent = {
        _root: {
            "t-on-slid.bs.carousel": this.onSlidCarousel,
        },
    };

    setup() {
        super.setup();

        this.innerCarouselEl = this.el.querySelector(".carousel-inner");
        this.originalItemsCount = this.innerCarouselEl.querySelectorAll(".carousel-item").length;
        this.cloneCarouselItems();
        this.showIndicators();

        this.innerCarouselEl.style.transition = "none";
        this.updateCarouselPosition(this.originalItemsCount);
        requestAnimationFrame(() => {
            this.innerCarouselEl.style.transition = "";
        });
    }

    destroy() {
        this.removeClonedItems();
        this.innerCarouselEl.style.transition = "none";
        this.updateCarouselPosition(0);
        this.setActiveIndicator(0);
        requestAnimationFrame(() => {
            this.innerCarouselEl.style.transition = "";
        });
        this.hideIndicators();
    }

    onSlidCarousel(event) {
        // we need to normalize the index to handle infinite scrolling,
        // indexes must always stay within the original items
        [event.to, event.from] = this.normalizeIndexes(event.to, event.from);
        this.slideCarousel(event.to, event.from);
    }

    async slideCarousel(to, from) {
        if (to === from) {
            return;
        }
        this.innerCarouselEl.style.transition = "none";
        this.updateCarouselPosition(from);
        this.setActiveIndicator(to);
        // Double RAF here to ensure the transition is applied correctly
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                this.innerCarouselEl.style.transition = "";
                this.updateCarouselPosition(to);
            });
        });
        return new Promise((resolve) => {
            this.innerCarouselEl.addEventListener("transitionend", resolve, { once: true });
        });
    }

    normalizeIndexes(to, from) {
        to = (to % this.originalItemsCount) + this.originalItemsCount;
        from = (from % this.originalItemsCount) + this.originalItemsCount;
        if (from === this.originalItemsCount && to === 2 * this.originalItemsCount - 1) {
            from = 2 * this.originalItemsCount;
        } else if (from === 2 * this.originalItemsCount - 1 && to === this.originalItemsCount) {
            from = this.originalItemsCount - 1;
        }

        return [to, from];
    }

    cloneCarouselItems() {
        const items = this.innerCarouselEl.querySelectorAll(
            ".carousel-item:not(.carousel-item_copy)"
        );
        const cloneItems = (items) => {
            const clonedItems = Array.from(items).map((item) => item.cloneNode(true));
            clonedItems.forEach((item) => {
                item.classList.add("carousel-item_copy");
                item.classList.remove("active");
                item.setAttribute("aria-hidden", "true");
            });
            return clonedItems;
        };
        this.innerCarouselEl.append(...cloneItems(items));
        this.innerCarouselEl.prepend(...cloneItems(items));
    }

    removeClonedItems() {
        const clonedItems = this.innerCarouselEl.querySelectorAll(".carousel-item_copy");
        clonedItems.forEach((item) => item.remove());
    }

    showIndicators() {
        const indicators = this.el.querySelectorAll(".carousel-indicators > *");
        indicators.forEach((indicator) => (indicator.style.display = "block"));
        this.hideIndicators = () => {
            const indicators = this.el.querySelectorAll(".carousel-indicators > *");
            indicators.forEach((indicator) => (indicator.style.display = ""));
        };
    }

    setActiveIndicator(index) {
        const indicators = this.el.querySelectorAll(".carousel-indicators > *");
        if (!indicators.length) {
            return;
        }
        indicators.forEach((indicator) => indicator.classList.remove("active"));
        indicators[index % this.originalItemsCount].classList.add("active");
    }

    updateCarouselPosition(index) {
        this.innerCarouselEl.style.transform =
            "translateX(calc(((100% - (var(--o-carousel-multiple-items-gap) * (var(--o-carousel-multiple-items) - 1))) / var(--o-carousel-multiple-items) + var(--o-carousel-multiple-items-gap)) * " +
            index +
            " * -1))";
    }
}

registry
    .category("public.interactions")
    .add("website.carousel_multiple_infinite_sliding", CarouselMultipleInfiniteSliding);
