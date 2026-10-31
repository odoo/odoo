import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

import { utils as uiUtils } from "@web/core/ui/ui_utils";

export class DynamicSnippetCarousel extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_carousel";
    static CHUNK_SIZE = 16;
    dynamicContent = {
        ...this.dynamicContent,
        _root: {
            ...this.dynamicContent._root,
            "t-on-slid.bs.carousel": this.onSlid,
        },
        ".carousel-control-prev": {
            "t-att-class": () => ({ invisible: this.hidePrev }),
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
     * @returns {number} The number of slides left before the last loaded
     * records are shown.
     */
    getSlidesLeft() {
        if (this.scrollMode === "single") {
            return this.fetchedData.length - this.recordsPerSlide - this.index;
        }
        const slideEls = this.carouselEl.querySelectorAll(".carousel-item");
        return slideEls.length - 1 - this.getActiveSlideIndex();
    }

    /**
     * Handles the 'slid' event of the carousel. Called *after* a slide
     * transition.
     *
     * @param {Event} ev The Bootstrap Carousel slid event.
     */
    async onSlid(ev) {
        const isRTL = !!this.el.closest(".o_rtl, [dir='rtl']");
        const isNext = ev.direction === (isRTL ? "right" : "left");
        isNext ? this.index++ : this.index--;
        this.computeHidePrev();
        if (this.hasMore && !this.isLoading && this.getSlidesLeft() <= 1) {
            this.isLoading = true;
            await this.fetchData();
            this.prepareContent();
            this.appendContent();
            this.isLoading = false;
            this.computeHidePrev();
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
        const { chunkSize, rowPerSlide } = this.getQWebRenderOptions();
        const slideSize = (this.scrollMode === "single" ? 1 : chunkSize) * rowPerSlide || 1;
        const chunk = DynamicSnippetCarousel.CHUNK_SIZE;
        const batchSize = Math.max(chunk - (chunk % slideSize), slideSize);
        this.limit = Math.min(batchSize, this.totalToFetch - offset);
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
        this.firstSlideEl = this.carouselEl.querySelector(".carousel-item");
        const recordsPerSlide = this.carouselEl.style.getPropertyValue("--o-carousel-chunk-size");
        this.recordsPerSlide = recordsPerSlide ? parseInt(recordsPerSlide) : 1;
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
            this.firstSlideEl.before(...newSlideEls.slice(oldInnerEl.childElementCount));
        } else {
            oldInnerEl.append(...newSlideEls.slice(oldInnerEl.childElementCount));
        }
        this.services["public.interactions"].startInteractions(templateAreaEl);
    }

    /**
     * @override
     */
    getQWebRenderOptions() {
        const renderOptions = super.getQWebRenderOptions(...arguments);
        const isSingleScroll = this.el.classList.contains("o_carousel_multi_items");
        const scrollMode =
            isSingleScroll && renderOptions.data.length > renderOptions.chunkSize
                ? "single"
                : "all";
        return Object.assign(renderOptions, {
            hidePrev: this.hasMore,
            interval: parseInt(this.el.dataset.carouselInterval),
            rowPerSlide: parseInt(uiUtils.isSmall() ? 1 : this.el.dataset.rowPerSlide || 1),
            scrollMode: scrollMode,
        });
    }
}

registry
    .category("public.interactions")
    .add("website.dynamic_snippet_carousel", DynamicSnippetCarousel);
