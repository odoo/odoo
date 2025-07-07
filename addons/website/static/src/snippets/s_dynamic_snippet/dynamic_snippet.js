import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { uniqueId } from "@web/core/utils/functions";
import { renderToFragment } from "@web/core/utils/render";
import { verifyHttpsUrl } from "@website/utils/misc";

import { markup } from "@odoo/owl";

const DEFAULT_NUMBER_OF_ELEMENTS = 4;
const DEFAULT_NUMBER_OF_ELEMENTS_SM = 1;

export class DynamicSnippet extends Interaction {
    static selector = ".s_dynamic_snippet";
    dynamicContent = {
        "[data-url]": {
            "t-on-click": this.callToAction,
        },
        _window: { "t-on-resize": this.throttled(this.render) },
        _root: {
            "t-att-class": () => ({
                o_dynamic_snippet_loading: this.loadingData,
            }),
        },
        ".missing_option_warning": {
            "t-att-class": () => ({
                "d-none": !!this.lastFetchedData.length,
            }),
        },
        ".s_dynamic_snippet_load_more": {
            "t-att-class": () => ({
                "d-none": !this.hasMore,
            }),
        },
        ".s_dynamic_snippet_load_more a": {
            "t-on-click.prevent.stop": this.locked(this.onLoadMore, true),
        },
    };

    setup() {
        this.lastFetchedData = [];
        this.renderedContentNode = document.createDocumentFragment();
        this.uniqueId = uniqueId("s_dynamic_snippet_");
        this.templateKey = "website.s_dynamic_snippet.grid";
        this.withSample = false;
        this.offset = 0;
        this.totalToFetch = parseInt(this.el.dataset.numberOfRecords) || 0;
        this.hasMore = false;
        this.fetchedData = [];
        this.chunkSize = 8;
    }

    async willStart() {
        this.isSingleMode =
            parseInt(this.el.dataset.numberOfRecords) === 1 && !this.el.dataset.filterId;
        await this.fetchData();
    }

    start() {
        this.render();
    }

    destroy() {
        // Clear content.
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        // Nested interactions are stopped implicitly.
        templateAreaEl.replaceChildren();
    }

    /**
     * Handles the "Load More" action.
     *
     * Fetches the next batch of records from the server and appends them to the
     * existing snippet content.
     */
    async onLoadMore() {
        await this.fetchData();
        this.prepareContent(this.lastFetchedData);
        this.appendContent();
    }

    /**
     * To be overridden
     * Check if additional configuration elements are required in order to fetch data.
     */
    isConfigComplete() {
        const data = this.el.dataset;
        const isSingleModeConfigComplete =
            data.snippetModel && (!this.withSample ? data.snippetResId : true);
        return !!(
            data.templateKey && (this.isSingleMode ? isSingleModeConfigComplete : data.filterId)
        );
    }

    /**
     * To be overridden
     * Provide a search domain if needed.
     */
    getSearchDomain() {
        return [];
    }

    /**
     * To be overridden
     * Add custom parameters if needed.
     */
    getRpcParameters() {
        return this.isSingleMode
            ? {
                  res_model: this.el.dataset.snippetModel,
                  res_id: parseInt(this.el.dataset.snippetResId),
              }
            : {};
    }

    async fetchData() {
        if (this.isConfigComplete()) {
            const remaining = this.totalToFetch - this.fetchedData.length;
            const limit = Math.min(this.chunkSize, remaining);
            const nodeData = this.el.dataset;
            const filterFragments = await this.waitFor(
                rpc(
                    "/website/snippet/filters",
                    Object.assign(
                        {
                            filter_id: parseInt(nodeData.filterId),
                            template_key: nodeData.templateKey,
                            limit,
                            offset: this.offset,
                            search_domain: this.getSearchDomain(),
                            with_sample: this.withSample,
                        },
                        this.getRpcParameters(),
                        JSON.parse(this.el.dataset?.customTemplateData || "{}")
                    )
                )
            );
            this.lastFetchedData = filterFragments.map(markup);
            this.fetchedData.push(...this.lastFetchedData);
            this.offset += limit;
            this.hasMore =
                this.fetchedData.length < this.totalToFetch &&
                this.lastFetchedData.length === limit;
        } else {
            this.lastFetchedData = [];
        }
    }

    /**
     * To be overridden
     * Prepare the content before rendering.
     * @param {Object[]} data The data items to be rendered in the snippet.
     */
    prepareContent(data) {
        this.renderedContentNode = renderToFragment(
            this.templateKey,
            this.getQWebRenderOptions(data)
        );
    }

    /**
     * To be overridden
     * Prepare QWeb options.
     * @param {Object[]} data The data items to be rendered in the snippet.
     */
    getQWebRenderOptions(data) {
        const dataset = this.el.dataset;
        const numberOfRecords = parseInt(dataset.numberOfRecords);
        let numberOfElements;
        if (uiUtils.isSmall()) {
            numberOfElements =
                parseInt(dataset.numberOfElementsSmallDevices) || DEFAULT_NUMBER_OF_ELEMENTS_SM;
        } else {
            numberOfElements = parseInt(dataset.numberOfElements) || DEFAULT_NUMBER_OF_ELEMENTS;
        }
        const chunkSize = numberOfRecords < numberOfElements ? numberOfRecords : numberOfElements;
        return {
            chunkSize: chunkSize,
            data,
            unique_id: this.uniqueId,
            extraClasses: dataset.extraClasses || "",
            columnClasses: dataset.columnClasses || "",
        };
    }

    render() {
        this.loadingData = false;
        if (this.lastFetchedData.length > 0 || this.withSample) {
            this.prepareContent(this.fetchedData);
        } else {
            this.renderedContentNode = document.createDocumentFragment();
        }
        this.renderContent();
        // TODO What was this about ? Rendered content is already started.
        // for (const childEl of this.el.children) {
        //     this.services["public.interactions"].startInteractions(childEl);
        // }
    }

    /**
     * Appends the newly fetched records to the existing snippet content.
     *
     * This method:
     *  - Renders only the latest batch of data(`this.lastFetchedData`).
     *  - Extracts the rendered item elements.
     *  - Appends those items to the snippet’s existing container.
     *
     * This incremental update is used by “Load More” behavior, allowing the
     * snippet to grow as additional data is fetched while preserving the
     * current DOM structure.
     */
    appendContent() {
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        // columnClasses templates have an extra wrapper.
        if (this.el.dataset.columnClasses) {
            const currentContentEl = templateAreaEl.firstElementChild;
            const newContentEl = this.renderedContentNode.firstElementChild;
            currentContentEl.append(...newContentEl.children);
        } else {
            templateAreaEl.append(this.renderedContentNode);
        }
        this.services["public.interactions"].startInteractions(templateAreaEl);
    }

    renderContent() {
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        this.services["public.interactions"].stopInteractions(templateAreaEl);
        templateAreaEl.replaceChildren(this.renderedContentNode);
        // TODO this is probably not the only public widget which creates DOM
        // which should be attached to another public widget. Maybe a generic
        // method could be added to properly do this operation of DOM addition.
        this.services["public.interactions"].startInteractions(templateAreaEl);
        // Same as above and probably should be done automatically for any
        // bootstrap behavior (apparently needed since BS 5.3): start potential
        // carousel in new content (according to their data-bs-ride and other
        // dataset attributes). Note: done here and not in dynamic carousel
        // extension, because: why not?
        // (TODO review + See interaction with "slider" public widget).
        this.waitForTimeout(() => {
            templateAreaEl.querySelectorAll(".carousel").forEach((carouselEl) => {
                if (carouselEl.dataset.bsInterval === "0") {
                    delete carouselEl.dataset.bsRide;
                    delete carouselEl.dataset.bsInterval;
                }
            });
        }, 0);
    }

    /**
     * Navigates to the call to action url.
     *
     * @param {Event} ev
     */
    callToAction(ev) {
        window.location = verifyHttpsUrl(ev.currentTarget.dataset.url);
    }
}

registry.category("public.interactions").add("website.dynamic_snippet", DynamicSnippet);
