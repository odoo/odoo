import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

import { utils as uiUtils } from "@web/core/ui/ui_service";

export class DynamicSnippetCarousel extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_carousel";
    static CHUNK_SIZE = 16;
    dynamicContent = {
        ...this.dynamicContent,
        _root: {
            ...this.dynamicContent._root,
            "t-on-slide.bs.carousel": this.onSlide,
            "t-on-slid.bs.carousel": this.computeHidePrev,
        },
        ".s_dynamic_snippet_content": {
            "t-att-class": () => ({ "d-none": this.isLoading }),
        },
        ".s_dynamic_content_holder": {
            "t-att-class": () => ({ "d-none": !this.isLoading }),
        },
        ".carousel-control-prev": {
            "t-att-class": () => ({ "d-none": this.hidePrev }),
        },
    };

    setup() {
        super.setup();
        this.templateKey = "website.s_dynamic_snippet.carousel";
        this.totalToFetch = 0;
        this.hasMore = false;
        this.fetchedData = [];
        this.isLoading = false;
        this.hidePrev = false;
        this.scrollMode = this.el.classList.contains("o_carousel_multi_items") ? "single" : "all";
    }

    async willStart() {
        this.totalToFetch = parseInt(this.el.dataset.numberOfRecords) || 0;
        await super.willStart();
    }

    start() {
        super.start();
        this.computeHidePrev();
    }

    /**
     * @returns {number} The index of the slide containing the "active" class.
     */
    getActiveSlideIndex() {
        const slideEls = this.carouselEl.querySelectorAll(".carousel-item");
        return [...slideEls].findIndex((s) => s.classList.contains("active"));
    }

    /**
     * Computes whether the "Previous" navigation button should be hidden.
     *
     * The button is hidden when backward navigation is not allowed:
     * - In "single" scroll mode: hidden when at the initial position as
     *   earlier slides may not exist yet due to lazy loading.
     * - In "all" scroll mode: hidden when on the first slide.
     *
     * This prevents users from navigating to non-existent previous slides.
     */
    computeHidePrev() {
        if (!this.carouselEl) {
            return;
        }
        if (this.scrollMode === "single") {
            this.hidePrev = this.hasMore && this.index === 0;
        } else {
            this.hidePrev = this.hasMore && this.getActiveSlideIndex() === 0;
        }
    }

    /**
     * Handles the carousel slide event and triggers lazy loading when needed.
     *
     * Tracks the current navigation position and loads more data when
     * approaching the end of available slides:
     * - In "all" scroll mode: triggers when reaching the last slide.
     * - In "single" scroll mode: triggers 4 items before the end to ensure
     *   smooth scrolling.
     *
     * Prevents the default slide behavior during data fetching, then manually
     * advances the carousel once new data is loaded.
     *
     * @param {Event} ev
     */
    async onSlide(ev) {
        ev.direction === "left" ? this.index++ : this.index--;
        const slideEls = this.carouselEl.querySelectorAll(".carousel-item");
        if (
            this.hasMore &&
            ((this.getActiveSlideIndex() === slideEls.length - 1 && ev.direction === "left") ||
                (this.scrollMode === "single" &&
                    this.index === this.fetchedData.length - this.itemsPerSlide))
        ) {
            ev.preventDefault();
            this.isLoading = true;
            this.updateContent(); // refresh immediately to update loading state
            await this.fetchData();
            this.prepareContent();
            this.appendContent();
            this.isLoading = false;
            this.updateContent();
            window.Carousel.getOrCreateInstance(this.carouselEl).next();
        }
    }

    /**
     * @override
     *
     * Fetches the next batch of records and accumulates them into
     * `this.fetchedData`.
     */
    async fetchData() {
        await super.fetchData();
        this.fetchedData.push(...this.data);
        this.hasMore =
            this.fetchedData.length < this.totalToFetch && this.data.length === this.limit;
        this.data = this.fetchedData;
    }

    /**
     * @override
     */
    getRpcParameters() {
        const offset = this.fetchedData.length;
        this.limit = Math.min(DynamicSnippetCarousel.CHUNK_SIZE, this.totalToFetch - offset);
        return {
            ...super.getRpcParameters(),
            limit: this.limit,
            offset,
        };
    }

    /**
     * @override
     *
     * Re-initializes carousel state after the DOM is replaced.
     *
     * The parent's renderContent() removes the old carousel element, so we
     * re-query carouselEl and create a new Bootstrap Carousel instance. The
     * index is reset since the first slide becomes visible after re-render.
     */
    renderContent() {
        super.renderContent();
        this.carouselEl = this.el.querySelector(".carousel");
        if (!this.carouselEl) {
            return;
        }
        this.index = 0;
        const itemsPerSlide = this.carouselEl.style.getPropertyValue("--o-carousel-chunk-size");
        this.itemsPerSlide = itemsPerSlide ? parseInt(itemsPerSlide) : 1;
        this.computeHidePrev();
    }

    /**
     * @override
     */
    appendContent() {
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        const oldInnerEl = templateAreaEl.querySelector(".carousel-inner");
        const newSlideEls = [...this.renderedContentNode.querySelector(".carousel-inner").children];
        newSlideEls[0].classList.remove("active");
        if (this.scrollMode === "single") {
            const newSlides = newSlideEls.slice(oldInnerEl.childElementCount);
            const referenceNodeEl = oldInnerEl.children[this.itemsPerSlide];
            newSlides.forEach((el) => oldInnerEl.insertBefore(el, referenceNodeEl));
        } else {
            oldInnerEl.append(...newSlideEls.slice(oldInnerEl.childElementCount));
        }
        this.services["public.interactions"].startInteractions(templateAreaEl);
    }

    /**
     * @override
     */
    getQWebRenderOptions(data) {
        const renderOptions = super.getQWebRenderOptions(...arguments);
        const isSingleScroll = this.el.classList.contains("o_carousel_multi_items");
        const scrollMode =
            isSingleScroll && renderOptions.data.length > renderOptions.chunkSize
                ? "single"
                : "all";
        return Object.assign(renderOptions, {
            interval: parseInt(this.el.dataset.carouselInterval),
            rowPerSlide: parseInt(uiUtils.isSmall() ? 1 : this.el.dataset.rowPerSlide || 1),
            scrollMode: scrollMode,
        });
    }
}

registry
    .category("public.interactions")
    .add("website.dynamic_snippet_carousel", DynamicSnippetCarousel);
