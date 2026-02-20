import { Interaction } from "@web/public/interaction";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";

export class CarouselSlider extends Interaction {
    static selector = ".carousel";
    dynamicContent = {
        _root: {
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
        ".carousel-indicators button, .carousel-indicators li": {
            "t-on-pointerdown": (ev) => {
                const toLoadEl = this.carouselItemEls.at(ev.currentTarget.dataset.bsSlideTo);
                this.prefetchImages([toLoadEl]);
            },
            "t-on-keydown": (ev) => {
                const hotkey = getActiveHotkey(ev);
                if (["space", "enter"].includes(hotkey)) {
                    const toLoadEl = this.carouselItemEls.at(ev.currentTarget.dataset.bsSlideTo);
                    this.prefetchImages([toLoadEl]);
                }
            },
        },
    };
    carouselOptions = undefined;

    setup() {
        this.maxHeight = undefined;
        this.carouselInnerEl = this.el.querySelector(".carousel-inner");
        this.carouselItemEls = [...this.carouselInnerEl.querySelectorAll(".carousel-item")];
    }

    start() {
        this.computeMaxHeight();
        this.updateContent();
        const carouselBS = window.Carousel.getOrCreateInstance(this.el, this.carouselOptions);
        this.registerCleanup(() => carouselBS.dispose());

        // Preload first items only when carousel is on screen
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    this.loadItemsToAppear();
                    observer.unobserve(this.el);
                }
            });
        });
        observer.observe(this.el);
        this.registerCleanup(() => observer.unobserve(this.el));
    }

    computeMaxHeight() {
        this.maxHeight = undefined;
        // "updateContent()" is necessary to reset the min-height before the
        // following check.
        this.updateContent();
        for (const itemEl of this.el.querySelectorAll(".carousel-item")) {
            const isActive = itemEl.classList.contains("active");
            itemEl.classList.add("active");
            const imageEl = itemEl.querySelector("img");
            imageEl?.removeAttribute("loading");
            const height = itemEl.getBoundingClientRect().height;
            if (height > this.maxHeight || this.maxHeight === undefined) {
                this.maxHeight = height;
            }
            itemEl.classList.toggle("active", isActive);
        }
    }

    /**
     * Handles the 'slid' event of the carousel. Called *after* a slide
     * transition.
     *
     * @param {Event} ev The Bootstrap Carousel slid event.
     */
    onSlidCarousel(ev) {
        this.loadItemsToAppear(); // Preload future items after a slide
    }

    /**
     * Loads images of the carousel-item necessary for both 'prev' and 'next'
     * animations. Loads images for items that are about to become visible.
     *
     * @param {number} [nbItemsToLoad=1] The number of items to preload on each
     * side.
     */
    loadItemsToAppear(nbItemsToLoad = 1) {
        const index = this.carouselItemEls.findIndex((el) => el.classList.contains("active"));
        const activeItemIndex = index >= 0 ? index : 0;

        // Load "Next" items: nbItemsToLoad items after the active element
        const nextEndIndex = Math.min(
            activeItemIndex + nbItemsToLoad + 1,
            this.carouselItemEls.length
        );
        const nextItemElsToLoad = this.carouselItemEls.slice(activeItemIndex, nextEndIndex);

        // load "Prev" items : nbItemsToLoad items before the active element
        // (circular wrapping)
        // if currentIndex is 0, then the nbItemsToLoad items are the last
        // elements of the carousel
        let prevItemElsToLoad = [];
        if (activeItemIndex - nbItemsToLoad < 0) {
            const wrapAmount = Math.abs(activeItemIndex - nbItemsToLoad);
            prevItemElsToLoad = this.carouselItemEls
                .slice(this.carouselItemEls.length - wrapAmount, this.carouselItemEls.length)
                .concat(this.carouselItemEls.slice(0, activeItemIndex))
                .reverse();
        } else {
            prevItemElsToLoad = this.carouselItemEls
                .slice(activeItemIndex - nbItemsToLoad, activeItemIndex)
                .reverse();
        }

        this.prefetchImages(nextItemElsToLoad.concat(prevItemElsToLoad));
    }
    /**
     * Replaces loading from `lazy` to `eager` for all images of the given
     * carousel slides. This forces the browser to load the images immediately.
     * The goal is to avoid the flicker (mainly on Firefox) when the carousel
     * slides.
     *
     * @param {HTMLElement[]} toLoadEls
     */
    prefetchImages(toLoadEls) {
        for (const carouselItemEl of toLoadEls) {
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
