import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { rpc } from "@web/core/network/rpc";
import { uniqueId } from "@web/core/utils/functions";
import { renderToElement } from "@web/core/utils/render";
import { listenSizeChange, utils as uiUtils } from "@web/core/ui/ui_service";

import { markup } from "@odoo/owl";

const DEFAULT_NUMBER_OF_ELEMENTS = 4;
const DEFAULT_NUMBER_OF_ELEMENTS_SM = 1;

export class DynamicSnippet extends Interaction {
    static selector = ".s_dynamic_snippet";
    dynamicContent = {
        "[data-url]": {
            "t-on-click": this.callToAction,
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
        this.renderedContentEl = document.createTextNode("");
        this.uniqueId = uniqueId("s_dynamic_snippet_");
        this.templateKey = "website.s_dynamic_snippet.grid";
    }
    async willStart() {
        return this.fetchData();
    }
    start() {
        this.registerCleanup(listenSizeChange(this.render.bind(this)));
        // TODO Editor behavior.
        // this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
        this.render();
        // TODO Editor behavior.
        // this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
    }
    destroy() {
        // TODO Editor behavior.
        // this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
        this.toggleVisibility(false);
        // Clear content.
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        // Nested interactions are stopped implicitly.
        templateAreaEl.replaceChildren();
        // TODO Editor behavior.
        // this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
    }
    /**
     * Method to be overridden in child components if additional configuration elements
     * are required in order to fetch data.
     */
    isConfigComplete() {
        return this.el.dataset.filterId !== undefined && this.el.dataset.templateKey !== undefined;
    }
    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     */
    getSearchDomain() {
        return [];
    }
    /**
     * Method to be overridden in child components in order to add custom parameters if needed.
     */
    getRpcParameters() {
        return {};
    }
    /**
     * Fetches the data.
     */
    async fetchData() {
        if (this.isConfigComplete()) {
            const nodeData = this.el.dataset;
            const filterFragments = await rpc(
                "/website/snippet/filters",
                Object.assign({
                        "filter_id": parseInt(nodeData.filterId),
                        "template_key": nodeData.templateKey,
                        "limit": parseInt(nodeData.numberOfRecords),
                        "search_domain": this.getSearchDomain(),
                        "with_sample": this.editableMode,
                    },
                    this.getRpcParameters(),
                    JSON.parse(this.el.dataset?.customTemplateData || "{}")
                )
            );
            this.data = filterFragments.map(markup);
        } else {
            this.data = [];
        }
    }
    /**
     * Method to be overridden in child components in order to prepare content
     * before rendering.
     */
    prepareContent() {
        this.renderedContentEl = renderToElement(
            this.templateKey,
            this.getQWebRenderOptions()
        );
    }
    /**
     * Method to be overridden in child components in order to prepare QWeb
     * options.
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
        if (this.data.length > 0 || this.editableMode) {
            this.el.classList.remove("o_dynamic_snippet_empty");
            this.prepareContent();
        } else {
            this.el.classList.add("o_dynamic_snippet_empty");
            this.renderedContentEl = document.createTextNode("");
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
        const mainPageUrl = this.getMainPageUrl();
        const allContentLink = this.el.querySelector(".s_dynamic_snippet_main_page_url");
        if (allContentLink && mainPageUrl) {
            allContentLink.href = mainPageUrl;
            allContentLink.classList.remove("d-none");
        }
        templateAreaEl.replaceChildren(this.renderedContentEl);
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
                window.Carousel.getInstance(carouselEl)?.dispose();
                if (!this.editableMode) {
                    window.Carousel.getOrCreateInstance(carouselEl);
                }
            });
        }, 0);
    }
    /**
     *
     * @param visible
     */
    toggleVisibility(visible) {
        this.el.classList.toggle("o_dynamic_snippet_empty", !visible);
    }
    /**
     * Returns the main URL of the module related to the active filter.
     */
    getMainPageUrl() {
        return "";
    }

    //------------------------------------- -------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Navigates to the call to action url.
     */
    callToAction(ev) {
        window.location = ev.currentTarget.dataset.url;
    }
}

registry.category("public.interactions").add("website.dynamic_snippet", DynamicSnippet);
