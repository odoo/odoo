import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class DynamicSnippetCarousel extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_carousel";
    dynamicContent = {
        ...this.dynamicContent,
        _root: {
            ...this.dynamicContent._root,
            "t-on-slid.bs.carousel": () => this.togglePrevButton(),
        }
    }

    setup() {
        super.setup();
        this.templateKey = "website.s_dynamic_snippet.carousel";
        this.offset = 0;
        this.chunkSize = 16;
        this.totalToFetch = 0;
        this.hasMore = true;
        this.fetchedData = [];
        this.intersectionObserver = null;
    }

    async willStart() {
        this.totalToFetch = parseInt(this.el.dataset.numberOfRecords) || 0;
        this.offset = 0;
        this.fetchedData = [];
        this.hasMore = true;
        await this.fetchMoreData();
    }

    start() {
        this.renderPreservingSlide();
        this.observeLastSlide();
    }

    destroy() {
        this.intersectionObserver?.disconnect();
        super.destroy();
    }

    renderPreservingSlide() {
        const slides = this.el.querySelectorAll(".carousel-inner .carousel-item");
        const activeIndex = Array.from(slides).findIndex(slide => slide.classList.contains("active"));

        this.render();

        this.waitForTimeout(() => {
            const newSlides = this.el.querySelectorAll(".carousel-inner .carousel-item");
            newSlides.forEach(slide => slide.classList.remove("active"));
            if (activeIndex >= 0 && activeIndex < newSlides.length) {
                newSlides[activeIndex].classList.add("active");
            } else if (newSlides.length > 0) {
                newSlides[0].classList.add("active");
            }
        }, 0);
    }

    togglePrevButton() {
        const carouselEl = this.el.querySelector(".carousel");
        const prevButton = this.el.querySelector(".carousel-control-prev");
        if (!carouselEl || !prevButton) {
            return;
        }

        const activeIndex = Array.from(carouselEl.querySelectorAll(".carousel-item"))
            .findIndex(el => el.classList.contains("active"));
        prevButton.classList.toggle("d-none", activeIndex === 0);
    }

    async fetchMoreData() {
        if (!this.hasMore) {
            return;
        }

        const remaining = this.totalToFetch - this.fetchedData.length;
        const limit = Math.min(this.chunkSize, remaining);
        if (limit <= 0) {
            this.hasMore = false;
            return;
        }

        const newFragments = (await this.fetchChunk(limit)).map(markup);
        this.fetchedData.push(...newFragments);
        this.data = this.fetchedData;
        this.offset += limit;

        this.hasMore = this.fetchedData.length < this.totalToFetch && newFragments.length === limit;
    }

    async fetchChunk(limit) {
        const { filterId, templateKey, customTemplateData } = this.el.dataset;
        return await this.waitFor(rpc("/website/snippet/filters", {
            filter_id: parseInt(filterId),
            template_key: templateKey,
            limit,
            offset: this.offset,
            search_domain: this.getSearchDomain(),
            ...this.getRpcParameters(),
            ...JSON.parse(customTemplateData || "{}"),
        }));
    }

    observeLastSlide() {
        if (!this.hasMore) {
            return;
        }

        const lastSlide = this.el.querySelector(".dynamic_snippet_template .carousel-inner > .carousel-item:last-child");
        if (!lastSlide) {
            return;
        }

        this.intersectionObserver?.disconnect();

        this.intersectionObserver = new IntersectionObserver(async (entries) => {
            for (const entry of entries) {
                if (entry.isIntersecting) {
                    this.intersectionObserver.unobserve(entry.target);

                    const carouselEl = this.el.querySelector(".carousel");
                    const carouselInstance = window.Carousel.getOrCreateInstance(carouselEl);
                    carouselInstance.pause();

                    await this.fetchMoreData();

                    carouselInstance.cycle();
                    this.renderPreservingSlide();
                    this.observeLastSlide();
                    break;
                }
            }
        }, {
            root: null,
            threshold: 0.01,
        });

        this.intersectionObserver.observe(lastSlide);
    }

    getQWebRenderOptions() {
        const scrollMode = this.el.classList.contains('o_carousel_multi_items') ? 'single' : 'all';
        return Object.assign(
            super.getQWebRenderOptions(...arguments),
            {
                interval: parseInt(this.el.dataset.carouselInterval),
                rowPerSlide: parseInt(uiUtils.isSmall() ? 1 : this.el.dataset.rowPerSlide || 1),
                arrowPosition: this.el.dataset.arrowPosition || "",
                scrollMode: scrollMode,
            },
        );
    }
}

registry
    .category("public.interactions")
    .add("website.dynamic_snippet_carousel", DynamicSnippetCarousel);
