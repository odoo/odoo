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
            "t-on-slide.bs.carousel": (ev) => this._onSlide(ev),
            "t-on-slid.bs.carousel": () => this.togglePrevButton(),
        },
    };

    setup() {
        super.setup();
        this.templateKey = "website.s_dynamic_snippet.carousel";
        this.offset = 0;
        this.chunkSize = 16;
        this.totalToFetch = 0;
        this.hasMore = true;
        this.fetchedData = [];
    }

    async willStart() {
        this.totalToFetch = parseInt(this.el.dataset.numberOfRecords) || 0;
        await this.fetchData();
    }

    start() {
        this.render();
        this.togglePrevButton();
    }

    /**
     * Called on slide event. Detects if last slide is reached and
     * load more data if available.
     */
    async _onSlide(ev) {
        const carouselEl = this.el.querySelector(".carousel");
        const items = carouselEl.querySelectorAll(".carousel-item");

        if (this.hasMore && ev.to === items.length - 1) {
            ev.preventDefault();

            let carousel = window.Carousel.getInstance(carouselEl);
            carousel.pause();

            const holder = this.el.querySelector(".s_dynamic_snippet_holder");
            const title = this.el.querySelector(".s_dynamic_snippet_title");
            const content = this.el.querySelector(".s_dynamic_snippet_content");
            title?.classList.add("d-none");
            content?.classList.add("d-none");
            holder?.classList.remove("d-none");

            await this.fetchData();
            this.render();

            holder?.classList.add("d-none");
            content?.classList.remove("d-none");
            title?.classList.remove("d-none");

            carousel = window.Carousel.getOrCreateInstance(carouselEl);
            carousel.cycle();
        }
    }

    /**
     * Show/hide the "Previous" arrow.
     *
     * Prevents users from navigating back from the first slide,
     * since lazy loading only adds slides when moving forward.
     */
    togglePrevButton() {
        const carouselEl = this.el.querySelector(".carousel");
        const prev = this.el.querySelector(".carousel-control-prev");
        if (!carouselEl || !prev) {
            return;
        }
        const idx = Array.from(carouselEl.querySelectorAll(".carousel-item")).findIndex((s) =>
            s.classList.contains("active")
        );
        if (idx === 0) {
            prev.classList.add("d-none");
        } else {
            prev.classList.remove("d-none");
        }
    }

    async fetchData() {
        if (!this.hasMore) {
            return;
        }
        const remaining = this.totalToFetch - this.fetchedData.length;
        const limit = Math.min(this.chunkSize, remaining);
        if (limit <= 0) {
            this.hasMore = false;
            return;
        }
        const newHtml = await this.fetchChunk(limit);
        const fragments = newHtml.map(markup);
        this.fetchedData.push(...fragments);
        this.data = this.fetchedData;
        this.offset += limit;
        this.hasMore = this.fetchedData.length < this.totalToFetch && fragments.length === limit;
    }

    async fetchChunk(limit) {
        const { filterId, templateKey, customTemplateData } = this.el.dataset;
        return this.waitFor(
            rpc("/website/snippet/filters", {
                filter_id: parseInt(filterId),
                template_key: templateKey,
                limit,
                offset: this.offset,
                search_domain: this.getSearchDomain(),
                ...this.getRpcParameters(),
                ...JSON.parse(customTemplateData || "{}"),
            })
        );
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
