/** @odoo-module native */
import { markup } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";
import { renderToFragment } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";
import { utils as uiUtils } from "@web/ui/viewport";
import { verifyHttpsUrl } from "@website/utils/misc";

const DEFAULT_NUMBER_OF_ELEMENTS = 4;
const DEFAULT_NUMBER_OF_ELEMENTS_SM = 1;

const log = makeLogger("website.dynamic_snippet");

export class DynamicSnippet extends Interaction {
    static selector = ".s_dynamic_snippet";
    dynamicContent = {
        "[data-url]": {
            "t-on-click": this.callToAction,
        },
        _window: { "t-on-resize": this.throttled(this.onWindowResize) },
        _root: {
            "t-att-class": () => ({
                o_dynamic_empty: !this.isVisible,
                s_dynamic_empty: !this.isVisible,
                o_dynamic_snippet_empty: !this.isVisible,
                o_dynamic_snippet_loading: !this.data.length,
            }),
        },
        ".missing_option_warning": {
            "t-att-class": () => ({
                "d-none": !!this.data.length,
            }),
        },
    };

    setup() {
        /**
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
            parseInt(this.el.dataset.numberOfRecords) === 1 &&
            !this.el.dataset.filterId;
        log.logic("willStart: mode", () => ({
            isSingleMode: this.isSingleMode,
            filterId: this.el.dataset.filterId,
            numberOfRecords: this.el.dataset.numberOfRecords,
        }));
        await this.fetchData();
    }

    start() {
        log.lifecycle("start", () => ({
            templateKey: this.templateKey,
            items: this.data.length,
        }));
        this.render();
    }

    destroy() {
        log.lifecycle("destroy: clearing rendered content");
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        templateAreaEl.replaceChildren();
    }

    isConfigComplete() {
        const data = this.el.dataset;
        const isSingleModeConfigComplete =
            data.snippetModel && (!this.withSample ? data.snippetResId : true);
        return !!(
            data.templateKey &&
            (this.isSingleMode ? isSingleModeConfigComplete : data.filterId)
        );
    }

    getSearchDomain() {
        return [];
    }

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
            const endFetch = log.perf(`fetch filter ${nodeData.filterId}`);
            const filterFragments = await this.waitFor(
                rpc(
                    "/website/snippet/filters",
                    Object.assign(
                        {
                            filter_id: parseInt(nodeData.filterId),
                            template_key: nodeData.templateKey,
                            limit: parseInt(nodeData.numberOfRecords),
                            search_domain: this.getSearchDomain(),
                            with_sample: this.withSample,
                        },
                        this.getRpcParameters(),
                        JSON.parse(this.el.dataset?.customTemplateData || "{}"),
                    ),
                ),
            );
            endFetch({
                template: nodeData.templateKey,
                fragments: filterFragments.length,
            });
            this.data = filterFragments.map(markup);
        } else {
            log.logic("fetchData", () => ({
                complete: false,
                dataset: { ...this.el.dataset },
            }));
            this.data = [];
        }
    }

    prepareContent() {
        const endPrepare = log.perf("prepareContent renderToFragment", () => ({
            templateKey: this.templateKey,
        }));
        this.renderedContentNode = renderToFragment(
            this.templateKey,
            this.getQWebRenderOptions(),
        );
        endPrepare();
    }

    getQWebRenderOptions() {
        const dataset = this.el.dataset;
        const numberOfRecords = parseInt(dataset.numberOfRecords);
        let numberOfElements;
        if (uiUtils.isSmall()) {
            numberOfElements =
                parseInt(dataset.numberOfElementsSmallDevices) ||
                DEFAULT_NUMBER_OF_ELEMENTS_SM;
        } else {
            numberOfElements =
                parseInt(dataset.numberOfElements) || DEFAULT_NUMBER_OF_ELEMENTS;
        }
        const chunkSize =
            numberOfRecords < numberOfElements ? numberOfRecords : numberOfElements;
        return {
            chunkSize: chunkSize,
            data: this.data,
            unique_id: this.uniqueId,
            extraClasses: dataset.extraClasses || "",
            columnClasses: dataset.columnClasses || "",
        };
    }

    onWindowResize() {
        // The output reads the viewport only through the small-device
        // breakpoint. Re-rendering on every resize looped in the website
        // preview: new content resized the iframe, which fired resize again.
        if (uiUtils.isSmall() !== this.renderedForSmallDevices) {
            this.render();
        }
    }

    render() {
        this.renderedForSmallDevices = uiUtils.isSmall();
        log.pipeline("render", () => ({
            items: this.data.length,
            withSample: this.withSample,
        }));
        if (this.data.length > 0 || this.withSample) {
            this.toggleVisibility(true);
            this.prepareContent();
        } else {
            this.toggleVisibility(false);
            this.renderedContentNode = document.createDocumentFragment();
        }
        this.renderContent();
    }

    renderContent() {
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        const endRenderContent = log.perf("renderContent restart interactions");
        this.services["public.interactions"].stopInteractions(templateAreaEl);
        templateAreaEl.replaceChildren(this.renderedContentNode);
        this.services["public.interactions"].startInteractions(templateAreaEl);
        endRenderContent(() => ({ nodes: templateAreaEl.childNodes.length }));
        this.waitForTimeout(() => {
            templateAreaEl.querySelectorAll(".carousel").forEach((carouselEl) => {
                if (carouselEl.dataset.bsInterval === "0") {
                    log.logic(
                        "renderContent: disabling carousel autoplay for interval 0",
                    );
                    delete carouselEl.dataset.bsRide;
                    delete carouselEl.dataset.bsInterval;
                }
            });
        }, 0);
    }

    /**
     * @param {Boolean} visible
     */
    toggleVisibility(visible) {
        this.isVisible = visible;
    }

    /**
     * @param {Event} ev
     */
    callToAction(ev) {
        log.logic("callToAction: navigating", () => ({
            url: ev.currentTarget.dataset.url,
        }));
        window.location = verifyHttpsUrl(ev.currentTarget.dataset.url);
    }
}

registry.category("public.interactions").add("website.dynamic_snippet", DynamicSnippet);
