import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CarouselSlider extends Interaction {
    static selector = ".carousel";
    dynamicContent = {
        _root: {
            "t-on-slide.bs.carousel": this.onSlideCarousel,
            "t-on-slid.bs.carousel": this.onSlidCarousel,
        },
        "img": {
            "t-on-load": this.computeMaxHeight,
        },
        _window: {
            "t-on-resize": this.debounced(this.computeMaxHeight, 250),
        },
        ".carousel-item": {
            "t-att-style": () => ({
                "min-height": this.maxHeight ? `${this.maxHeight}px` : "",
            }),
        },
    };
    carouselOptions = undefined;

    static OLD_AUTO_SLIDING_SNIPPETS = ["s_image_gallery"];
    setup() {
        this.maxHeight = undefined;
        this.hasInterval = ![undefined, "false", "0"].includes(this.el.dataset.bsInterval);
        if (!this.hasInterval || !this.el.dataset.bsRide) {
            // If bsInterval is 0, false or undefined, it means no auto slide
            window.Carousel.getOrCreateInstance(this.el, { ride: false, pause: true });
            this.el.dataset.bsRide = "noAutoSlide";
        } else if (this.hasInterval && this.el.dataset.bsRide === "noAutoSlide") {
            // Restore auto-slide if explicitly enabled, except for legacy snippets
            const snippetName = this.el.closest("[data-snippet]")?.dataset.snippet;
            this.el.dataset.bsRide = this.constructor.OLD_AUTO_SLIDING_SNIPPETS.includes(
                snippetName
            )
                ? "carousel"
                : "true";
        }
    }

    start() {
        this.computeMaxHeight();
        this.updateContent();
        const carouselBS = window.Carousel.getOrCreateInstance(this.el, this.carouselOptions);
        this.registerCleanup(() => carouselBS.dispose());

        this.carouselInnerEl = this.el.querySelector(".carousel-inner");

        const itemWidth = getComputedStyle(this.el).getPropertyValue("--o-carousel-item-width-percentage");
        const itemsPerSlide = itemWidth ? Math.round(100 / parseFloat(itemWidth)) : 1;
        this.options = {
            scrollMode: this.el.classList.contains('o_carousel_multi_items') ? 'single' : 'all',
            itemsPerSlide: itemsPerSlide,
        };

        // Preload first items only when carousel is on screen
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadItemsToAppear();
                    observer.unobserve(this.el);
                }
            });
        });
        observer.observe(this.el);
    }

    computeMaxHeight() {
        this.maxHeight = undefined;
        // "updateContent()" is necessary to reset the min-height before the
        // following check.
        this.updateContent();
        for (const itemEl of this.el.querySelectorAll(".carousel-item")) {
            const isActive = itemEl.classList.contains("active");
            itemEl.classList.add("active");
            const height = itemEl.getBoundingClientRect().height;
            if (height > this.maxHeight || this.maxHeight === undefined) {
                this.maxHeight = height;
            }
            itemEl.classList.toggle("active", isActive);
        }
    }

    /**
     * Handles the 'slide' event of the carousel. Called *before* a slide
     * transition.
     *
     * @param {Event} ev The Bootstrap Carousel slide event.
     */
    onSlideCarousel(ev) {
        const imageEls = [...this.carouselInnerEl.querySelectorAll("img")];
        const isLoading = imageEls.some(el => el.loading !== "lazy" && !el.complete);
        if (isLoading) {
            // If images are loading, prevent the slide transition. It will
            // slide once the next images are loaded.
            ev.preventDefault();
            return;
        }
        if (this.options.scrollMode === "single") {
            this.onSlideSingleScroll(ev);
        }
    }

    /**
     * Handles the 'slid' event of the carousel. Called *after* a slide
     * transition.
     *
     * @param {Event} ev The Bootstrap Carousel slid event.
     */
    onSlidCarousel(ev) {
        if (this.options.scrollMode === "single") {
            this.onSlidSingleScroll(ev);
        }
        this.loadItemsToAppear(); // Preload future items after a slide
    }

    /**
     * Manages multi-items single-scroll behavior during the 'slide' event.
     * Prepares the DOM for smooth transitions by moving elements.
     *
     * @param {Event} ev The Bootstrap Carousel slide event.
     */
    onSlideSingleScroll(ev) {
        // We need to keep the active element at the beginning of the carousel-items elements
        // This allows to have a smooth transition when the carousel is sliding
        if (ev.direction === "right") {
            const carouselItemsEls = Array.from(this.carouselInnerEl.querySelectorAll(".carousel-item"));
            this.carouselInnerEl.prepend(carouselItemsEls.pop());
        }
    }

    /**
     * Manages single-item scroll behavior during the 'slid' event.
     * Completes the DOM manipulation started in `onSlideSingleScroll`.
     *
     * @param {Event} ev The Bootstrap Carousel slid event.
     */
    onSlidSingleScroll(ev) {
        // As for the onSlideSingleScroll method, we need to keep the active
        // element at the beginning of the carousel-items list in the DOM. So
        // when animation is done, we move the first item (which is not active
        // anymore) to the end.
        if (ev.direction === "left") {
            const carouselItemsEls = this.carouselInnerEl.querySelectorAll(".carousel-item");
            this.carouselInnerEl.appendChild(carouselItemsEls[0]);
        }
    }

    /**
     * Loads images of the carousel-item necessary for both 'prev' and 'next'
     * animations. Loads images for items that are about to become visible.
     *
     * @param {number} [nbItemsToLoad=1] The number of items to preload on each side.
     */
    loadItemsToAppear(nbItemsToLoad = 1) {
        const itemEls = Array.from(this.carouselInnerEl.children);
        const index = itemEls.findIndex(el => el.classList.contains("active"));
        const activeItemIndex = index >= 0 ? index : 0;

        // Load "Next" items: nbItemsToLoad items after the active element
        const nbItemElsOnScreen = this.options.scrollMode === "single" ? this.options.itemsPerSlide + 1 : 1;
        const nextEndIndex = Math.min(activeItemIndex + nbItemElsOnScreen + nbItemsToLoad + 1, itemEls.length);
        const nextItemElsToLoad = itemEls.slice(activeItemIndex, nextEndIndex);

        // load "Prev" items : nbItemsToLoad items before the active element (circular wrapping)
        // if currentIndex is 0, then the nbItemsToLoad items are the last elements of the carousel
        let prevItemElsToLoad = [];
        if (activeItemIndex - nbItemsToLoad < 0) {
            const wrapAmount = Math.abs(activeItemIndex - nbItemsToLoad);
            prevItemElsToLoad = itemEls.slice(itemEls.length - wrapAmount, itemEls.length).reverse().concat(itemEls.slice(0, activeItemIndex).reverse());
        } else {
            prevItemElsToLoad = itemEls.slice(Math.max(0, activeItemIndex - nbItemsToLoad), activeItemIndex).reverse();
        }

        // Set the `loading` attribute of lazy-loaded images to `eager` for the
        // given carousel items. This forces the browser to load the images
        // immediately.
        const itemsToLoad = nextItemElsToLoad.concat(prevItemElsToLoad);
        for (let carouselItemEl of itemsToLoad) {
            const imageEls = carouselItemEl.querySelectorAll("img[loading='lazy']");
            for (const imageEl of imageEls) {
                // Note that we remove the attribute with the goal of forcing it
                // to the "eager" value. Removing the attribute is better so
                // that the attribute is not saved as eager in edit mode (the
                // lazy value is auto added on page rendering).
                imageEl.removeAttribute("loading");
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website.carousel_slider", CarouselSlider);
