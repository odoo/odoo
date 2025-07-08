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
        ".missing_option_warning": {
            "t-att-class": () => ({
                "d-none": !!this.data.length,
            }),
        },
    };

    setup() {
        /**
         * The dynamic filter data source data formatted with the chosen template.
         * Can be accessed when overriding the _render_content() function in order to generate
         * a new renderedContent from the original data.
         *
         * @type {*|jQuery.fn.init|jQuery|HTMLElement}
         */
        this.data = [];
        this.renderedContentNode = document.createDocumentFragment();
        this.uniqueId = uniqueId("s_dynamic_snippet_");
        this.templateKey = "website.s_dynamic_snippet.grid";
        this.withSample = false;
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
            const nodeData = this.el.dataset;
            const filterFragments = await this.waitFor(rpc(
                "/website/snippet/filters",
                Object.assign({
                    "filter_id": parseInt(nodeData.filterId),
                    "template_key": nodeData.templateKey,
                    "limit": parseInt(nodeData.numberOfRecords),
                    "search_domain": this.getSearchDomain(),
                    "with_sample": this.withSample,
                },
                    this.getRpcParameters(),
                    JSON.parse(this.el.dataset?.customTemplateData || "{}")
                )
            ));
            this.data = filterFragments.map(markup);
        } else {
            this.data = [];
        }
    }

    /**
     * To be overridden
     * Prepare the content before rendering.
     */
    prepareContent() {
        this.renderedContentNode = renderToFragment(
            this.templateKey,
            this.getQWebRenderOptions()
        );
    }

    /**
     * To be overridden
     * Prepare QWeb options.
     */
    getQWebRenderOptions() {
        const dataset = this.el.dataset;
        const numberOfRecords = parseInt(dataset.numberOfRecords);
        let numberOfElements;
        if (uiUtils.isSmall()) {
            numberOfElements = parseInt(dataset.numberOfElementsSmallDevices) || DEFAULT_NUMBER_OF_ELEMENTS_SM;
        } else {
            numberOfElements = parseInt(dataset.numberOfElements) || DEFAULT_NUMBER_OF_ELEMENTS;
        }
        const chunkSize = numberOfRecords < numberOfElements ? numberOfRecords : numberOfElements;
        return {
            chunkSize: chunkSize,
            data: this.data,
            unique_id: this.uniqueId,
            extraClasses: dataset.extraClasses || "",
            columnClasses: dataset.columnClasses || "",
        };
    }

    render() {
        if (this.data.length > 0 || this.withSample) {
            this.prepareContent();
        } else {
            this.renderedContentNode = document.createDocumentFragment();
        }
        this.renderContent();
        // TODO What was this about ? Rendered content is already started.
        // for (const childEl of this.el.children) {
        //     this.services["public.interactions"].startInteractions(childEl);
        // }
    }

    renderContent() {
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        this.services["public.interactions"].stopInteractions(templateAreaEl);
        templateAreaEl.replaceChildren(this.renderedContentNode);
        this.el.classList.remove("o_dynamic_snippet_empty");
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
            templateAreaEl.querySelectorAll(".carousel").forEach(carouselEl => {
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

registry
    .category("public.interactions")
    .add("website.dynamic_snippet", DynamicSnippet);
