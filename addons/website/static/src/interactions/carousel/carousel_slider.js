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
                "min-height": `${this.maxHeight}px`,
            }),
        },
    };
    carouselOptions = undefined;

    setup() {
        this.maxHeight = undefined;
    }

    start() {
        this.computeMaxHeight();
        this.updateContent();
        const carouselBS = window.Carousel.getOrCreateInstance(this.el, this.carouselOptions);
        this.registerCleanup(() => carouselBS.dispose());

        this.carouselInnerEl = this.el.querySelector(".carousel-inner");
        this.options = {
            scrollMode: this.el.dataset.scrollMode,
            itemsPerSlide: parseInt(this.el.dataset.itemsPerSlide) || 1,
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
     * Handles the 'slide' event of the carousel.  Called *before* a slide transition.
     *
     * @param {Event} ev The Bootstrap Carousel slide event.
     */
    onSlideCarousel(ev) {
        if (this.isImageLoading()) {
            ev.preventDefault();
            return;
        }
        if (this.options.scrollMode === "single") {
            this.onSlideSingleScroll(ev);
        }
    }

    /**
     * Handles the 'slid' event of the carousel. Called *after* a slide transition.
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
     * Manages single-item scroll behavior during the 'slide' event.
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
        // As for the _onSlide method, we need to keep the active element at the
        // beginning of the carousel-items list in the DOM. So when animation is
        // done, we move the first item (which is not active anymore) to the end
        if (ev.direction === "left") {
            const carouselItemsEls = Array.from(this.carouselInnerEl.querySelectorAll(".carousel-item"));
            this.carouselInnerEl.appendChild(carouselItemsEls[0]);
        }
    }

    /**
     * Loads images of the carousel-item necessary for both 'prev' and 'next' animations.
     * Loads images for items that are about to become visible.
     *
     * @param {number} [nItemsToLoad=1] The number of items to preload on each side.
     */
    loadItemsToAppear(nItemsToLoad = 1) {
        const itemEls = Array.from(this.carouselInnerEl.children);
        const activeItemEl = this.carouselInnerEl.querySelector(".active");
        const activeItemIndex = (activeItemEl && itemEls.indexOf(activeItemEl) !== -1) ? itemEls.indexOf(activeItemEl) : 0;

        // load "Next" items: nItemsToLoad items after the active element
        const nItemElsOnScreen = this.options.scrollMode === "single" ? this.options.itemsPerSlide + 1 : 1;
        const nextEndIndex = Math.min(activeItemIndex + nItemElsOnScreen + nItemsToLoad + 1, itemEls.length);
        const nextItemElsToLoad = itemEls.slice(activeItemIndex, nextEndIndex);

        // load "Prev" items : nItemsToLoad items before the active element (circular wrapping)
        // if currentIndex is 0, then the nItemsToLoad items are the last elements of the carousel
        let prevItemElsToLoad = [];
        if (activeItemIndex - nItemsToLoad < 0) {
            const wrapAmount = Math.abs(activeItemIndex - nItemsToLoad);
            prevItemElsToLoad = itemEls.slice(itemEls.length - wrapAmount, itemEls.length).reverse().concat(itemEls.slice(0, activeItemIndex).reverse());
        } else {
            prevItemElsToLoad = itemEls.slice(Math.max(0, activeItemIndex - nItemsToLoad), activeItemIndex).reverse();
        }

        this.loadItemImages(nextItemElsToLoad.concat(prevItemElsToLoad));
    }

    /**
     * Sets the `loading` attribute of lazy-loaded images to `eager` for the given carousel items.
     * This forces the browser to load the images immediately.
     *
     * @param {Array<HTMLElement>} itemsToLoad An array of carousel item elements.
     */
    loadItemImages(itemsToLoad) {
        for (let carouselItemEl of itemsToLoad) {
            carouselItemEl.querySelectorAll("img[loading='lazy']").forEach(imageEl => {
                imageEl.setAttribute("loading", "eager");
            });
        }
    }

    /**
     * Checks if any images within the carousel are currently loading.
     *
     * @returns {boolean} True if any image is loading, false otherwise.
     */
    isImageLoading() {
        const imageEls = this.carouselInnerEl.querySelectorAll("img");
        for (const imageEl of imageEls) {
            if (imageEl.loading !== "lazy") {
                if (!imageEl.complete) {
                    return true;
                }
            }
        }
        return false;
    }
}

registry
    .category("public.interactions")
    .add("website.carousel_slider", CarouselSlider);
