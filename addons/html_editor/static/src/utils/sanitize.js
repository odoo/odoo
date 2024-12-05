import { BaseContainer } from "@html_editor/core/base_container";
import { childNodesAnalysis } from "../utils/dom_info";
import { wrapInlinesInBlocks } from "./dom";

export function initElementForEdition(element, options = {}) {
    const analysis = childNodesAnalysis(element);
    if (analysis.inline.length && !options.allowInlineAtRoot) {
        // Use a baseContainer without margin bottom for this operation
        // TODO ABD: specify why the margin-bottom spec was in place in the
        // first place ?
        wrapInlinesInBlocks(element, {
            baseContainer: new BaseContainer("DIV", element.ownerDocument),
        });
    }
}

export function fixInvalidHTML(content) {
    const regex = /<\s*(a|strong)[^<]*?\/\s*>/g;
    return content.replace(regex, (match, g0) => match.replace(/\/\s*>/, `></${g0}>`));
}
