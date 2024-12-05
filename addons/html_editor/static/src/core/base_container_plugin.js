import {
    childNodesAnalysis,
    isEligibleForBaseContainer,
    isProtected,
    isProtecting,
} from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { unwrapContents, wrapInlinesInBlocks } from "@html_editor/utils/dom";
import { BASE_CONTAINER_CLASS, BaseContainer } from "./base_container";

export class BaseContainerPlugin extends Plugin {
    static id = "baseContainer";
    static shared = ["getBaseContainer", "normalizeDivBaseContainers", "setBaseContainer"];
    baseContainer = new BaseContainer(this.config.baseContainer, this.document);
    resources = {
        copy_attributes_handlers: (attributes, source) => {
            const baseContainerAttributes =
                BaseContainer.getBaseContainer(source, this.document)?.attributes || {};
            Object.assign(attributes, baseContainerAttributes);
        },
        // check if normalize_handlers is too expensive/useless
        normalize_handlers: this.normalizeDivBaseContainers.bind(this),
        start_edition_handlers: this.normalizeDivBaseContainers.bind(this),
    };

    setBaseContainer(tagName) {
        this.baseContainer = new BaseContainer(tagName, this.document);
    }

    getBaseContainer() {
        return this.baseContainer;
    }

    normalizeDivBaseContainers(element = this.editable) {
        const divBaseContainer = new BaseContainer("DIV", this.document);
        for (const div of element.querySelectorAll(`div:not(.${BASE_CONTAINER_CLASS})`)) {
            if (isEligibleForBaseContainer(div)) {
                div.classList.add(BASE_CONTAINER_CLASS);
            } else if (div.isContentEditable && !isProtected(div) && !isProtecting(div)) {
                // editable + not protected + contains flow content
                // => not eligible to be a "paragraph"
                // what to do with these nodes ? -> split their content
                // into eligible parts and create a base container for them
                // => specify what to use instead of "P" in wrapInlines
                wrapInlinesInBlocks(div, { baseContainer: divBaseContainer });
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
            if (div.parentElement.matches(`.${BASE_CONTAINER_CLASS}`)) {
                unwrapContents(div);
            } else {
                const analysis = childNodesAnalysis(div.parentElement);
                if (analysis.inline.length) {
                    wrapInlinesInBlocks(div.parentElement, { baseContainer: divBaseContainer });
                }
            }
        }
    }
}
