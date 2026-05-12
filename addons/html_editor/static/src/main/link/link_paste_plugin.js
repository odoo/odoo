import { childNodes, closestElement } from "@html_editor/utils/dom_traversal";
import { URL_REGEX, cleanZWChars } from "./utils";
import { isImageUrl } from "@html_editor/utils/url";
import { Plugin } from "@html_editor/plugin";
import { childNodeIndex } from "@html_editor/utils/position";
import { findInSelection } from "@html_editor/utils/selection";

const splitTextAroundUrl = (text) => {
    // todo: add placeholder plugin that prevent any other plugin
    // Avoid transforming dynamic placeholder pattern to url.
    if (!text.match(/\${.*}/gi)) {
        const splitAroundUrl = text.split(URL_REGEX);
        // Remove 'http(s)://' capturing group from the result
        // (indexes 2, 5, 8, ...).
        return splitAroundUrl.filter((_, index) => (index + 1) % 3);
    }
};
export const isSingleUrl = (text) => {
    const splitAroundUrl = Array.isArray(text) ? text : splitTextAroundUrl(text);
    return (
        hasUrls(splitAroundUrl) &&
        splitAroundUrl.length === 3 &&
        !splitAroundUrl[0] &&
        !splitAroundUrl[2]
    );
};
const hasUrls = (splitAroundUrl) => splitAroundUrl && splitAroundUrl.length >= 3;

export class LinkPastePlugin extends Plugin {
    static id = "linkPaste";
    static dependencies = ["link", "clipboard", "selection", "dom", "history", "delete"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        on_will_paste_handlers: this.selectFullySelectedLink.bind(this),
        fragment_to_insert_processors: this.processFragmentToInsert.bind(this),
    };

    processFragmentToInsert(fragment) {
        const selection = this.dependencies.selection.getEditableSelection();
        const selectionIsInsideALink = !!closestElement(selection.anchorNode, "a");
        const selectionIsInsideAPre = !!closestElement(selection.anchorNode, "pre");
        for (const node of childNodes(fragment)) {
            if (node.nodeType === Node.TEXT_NODE && !selectionIsInsideAPre) {
                const splitAroundUrl = splitTextAroundUrl(node.textContent);
                if (isSingleUrl(splitAroundUrl)) {
                    // Pasted content is a single URL.
                    const text = node.textContent;
                    const url = /^https?:\/\//i.test(text) ? text : "https://" + text;
                    if (selectionIsInsideALink && isImageUrl(url)) {
                        const img = this.document.createElement("IMG");
                        img.setAttribute("src", url);
                        node.before(img);
                        node.remove();
                    } else if (!selectionIsInsideALink) {
                        let label;
                        const selectedText = cleanZWChars(selection.toString());
                        if (!selection.isCollapsed && selectedText.length) {
                            // If the entire link is selected and its label matches the URL,
                            // replace the existing link with the new URL.
                            const link = findInSelection(selection, "a");
                            if (link) {
                                const linkLabel = cleanZWChars(link.textContent);
                                const href = link.getAttribute("href");
                                const labelMatchesHref =
                                    linkLabel === href ||
                                    linkLabel + "/" === href ||
                                    linkLabel === href + "/";
                                label = labelMatchesHref ? text : selectedText;
                            } else {
                                label = selectedText;
                            }
                        } else {
                            label = text;
                        }
                        node.before(this.dependencies.link.createLink(url, label));
                        node.remove();
                    }
                } else if (hasUrls(splitAroundUrl)) {
                    // Pasted content is multiple URLs.
                    for (let i = 0; i < splitAroundUrl.length; i++) {
                        const text = splitAroundUrl[i];
                        const url = /^https?:\/\//gi.test(text) ? text : "https://" + text;
                        // Even indexes will always be plain text, and odd
                        // indexes will always be URL. A url cannot be
                        // transformed inside an existing link.
                        if (i % 2 && !selectionIsInsideALink) {
                            node.before(this.dependencies.link.createLink(url, text));
                        } else if (text !== "") {
                            node.before(this.document.createTextNode(text));
                        }
                    }
                    node.remove();
                }
            }
        }
        return fragment;
    }

    /**
     * @param {EditorSelection} selection
     */
    selectFullySelectedLink(selection) {
        const link = closestElement(selection.anchorNode, "a");
        if (
            link?.parentElement?.isContentEditable &&
            cleanZWChars(selection.toString()) === cleanZWChars(link.innerText) &&
            !this.dependencies.delete.isUnremovable(link)
        ) {
            this.dependencies.selection.setSelection(
                {
                    anchorNode: link.parentElement,
                    anchorOffset: childNodeIndex(link) + (selection.direction ? 0 : 1),
                    focusNode: link.parentElement,
                    focusOffset: childNodeIndex(link) + (selection.direction ? 1 : 0),
                },
                { normalize: false }
            );
        }
    }
}
