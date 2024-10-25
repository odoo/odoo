import {
    childNodesAnalysis,
    isMediaElement,
    isProtected,
    isProtecting,
} from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { fillEmpty, unwrapContents } from "@html_editor/utils/dom";
import { BASE_CONTAINER_CLASS, BaseContainer } from "../utils/base_container";
import { closestElement } from "@html_editor/utils/dom_traversal";

export class BaseContainerPlugin extends Plugin {
    static id = "baseContainer";
    static shared = ["getBaseContainer", "normalizeDivBaseContainers"];
    baseContainer = new BaseContainer(this.config.baseContainer, this.document);
    resources = {
        copy_attributes_handlers: (attributes, source) => {
            const baseContainerAttributes =
                BaseContainer.getBaseContainer(source, this.document)?.attributes || {};
            Object.assign(attributes, baseContainerAttributes);
        },
        // check if normalize_handlers is too expensive/useless
        normalize_handlers: this.normalizeDivBaseContainers.bind(this),
        // start_edition_handlers: this.normalizeDivBaseContainers.bind(this),
    };

    getBaseContainer() {
        return this.baseContainer;
    }

    normalizeDivBaseContainers(element = this.editable) {
        // TODO ABD: should we handle "P" elements too ? (prevent P inside div, unwrapContents inside P, etc.. )
        // const divBaseContainer = new BaseContainer("DIV", this.document);
        for (const div of element.querySelectorAll(`div:not(.${BASE_CONTAINER_CLASS})`)) {
            const isContentEditable = (el) =>
                el.isContentEditable ||
                (!el.isConnected && !closestElement(el, "[contenteditable]"));
            if (
                isContentEditable(div) &&
                !isProtected(div) &&
                !isProtecting(div) &&
                !isMediaElement(div) && // TODO ABD: to discuss, but a div with .o_image should probably
                // be `contenteditable=false` too, and in that case, this check is unnecessary
                !this.delegateTo("assign_base_container_overrides", div)
            ) {
                const analysis = childNodesAnalysis(div);
                if (analysis.flowContent.length === 0) {
                    div.classList.add(BASE_CONTAINER_CLASS);
                    if (analysis.childNodes.length === 0) {
                        fillEmpty(div);
                    }
                }
                // else {
                //     // TODO ABD: not the job of this normalize function (see sanitize)
                //     //
                //     // editable + not protected + contains flow content
                //     // => not eligible to be a "paragraph"
                //     // what to do with these nodes ? -> split their content
                //     // into eligible parts and create a base container for them
                //     // => specify what to use instead of "P" in wrapInlines
                //     // wrapInlinesInBlocks(div, { baseContainer: divBaseContainer });
                // }
            }
        }
        // => we should ensure that `div+paragraph` elements only contain phrasing content, P and
        // DIV should be interchangeable => check unwrap/wrap thingies
        // wrapInlinesInBlocks for siblings of BASE_CONTAINER_CLASS
        // unwrapContents if BASE_CONTAINER_CLASS is a child of BASE_CONTAINER_CLASS
        const divBaseContainers = [
            ...element.querySelectorAll(`div.${BASE_CONTAINER_CLASS}`),
        ].reverse();
        for (const div of divBaseContainers) {
            // TODO ABD: there may be "DIVS" that match some condition which can not
            // be unwrapped (i.e. check website layout divs)
            if (div.parentElement.matches(BaseContainer.selector)) {
                unwrapContents(div);
            }
            // else {
            //     // TODO ABD: not the job of this normalize function (see sanitize)
            //     // allow inline elements next to blocks, like before
            //     //
            //     // const analysis = childNodesAnalysis(div.parentElement);
            //     // if (analysis.inline.length) {
            //     //     wrapInlinesInBlocks(div.parentElement, { baseContainer: divBaseContainer });
            //     // }
            // }
        }
    }
}
