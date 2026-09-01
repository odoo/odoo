/** @odoo-module native */
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { childNodeIndex } from "@html_editor/utils/position";
import { isImageUrl } from "@html_editor/utils/url";

import { cleanZWChars, URL_REGEX } from "./utils.js";

/**
 * @typedef {((text: string, url: string) => void | true)[]} paste_url_overrides
 */

export class LinkPastePlugin extends Plugin {
    static id = "linkPaste";
    static dependencies = ["link", "clipboard", "selection", "dom", "history"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        before_paste_handlers: this.selectFullySelectedLink.bind(this),
        paste_text_overrides: this.handlePasteText.bind(this),
    };

    /**
     * @param {EditorSelection} selection
     * @param {string} text
     */
    handlePasteText(selection, text) {
        let splitAroundUrl;
        if (!text.match(/\${.*}/gi)) {
            splitAroundUrl = text.split(URL_REGEX);
            splitAroundUrl = splitAroundUrl.filter((_, index) => (index + 1) % 3);
        }
        if (
            !splitAroundUrl ||
            splitAroundUrl.length < 3 ||
            closestElement(selection.anchorNode, "pre")
        ) {
            return false;
        }
        if (splitAroundUrl.length === 3 && !splitAroundUrl[0] && !splitAroundUrl[2]) {
            this.handlePasteTextUrl(selection, text);
        } else {
            this.handlePasteTextMultiUrl(selection, splitAroundUrl);
        }
        return true;
    }
    /**
     * @param {EditorSelection} selection
     * @param {string} text
     */
    handlePasteTextUrl(selection, text) {
        const selectionIsInsideALink = !!closestElement(selection.anchorNode, "a");
        const url = /^https?:\/\//i.test(text) ? text : "http://" + text;
        if (selectionIsInsideALink) {
            this.handlePasteTextUrlInsideLink(text, url);
            return;
        }
        if (this.delegateTo("paste_url_overrides", text, url)) {
            return;
        }
        const label =
            !selection.isCollapsed && cleanZWChars(selection.textContent()).length
                ? selection.textContent()
                : text;
        this.dependencies.link.insertLink(url, label);
    }
    /**
     * @param {string} text
     * @param {string} url
     */
    handlePasteTextUrlInsideLink(text, url) {
        if (isImageUrl(url)) {
            const img = this.document.createElement("IMG");
            img.setAttribute("src", url);
            this.dependencies.dom.insert(img);
        } else {
            this.dependencies.dom.insert(text);
        }
    }
    /**
     * @param {EditorSelection} selection
     * @param {string[]} splitAroundUrl
     */
    handlePasteTextMultiUrl(selection, splitAroundUrl) {
        const selectionIsInsideALink = !!closestElement(selection.anchorNode, "a");
        for (let i = 0; i < splitAroundUrl.length; i++) {
            const url = /^https?:\/\//gi.test(splitAroundUrl[i])
                ? splitAroundUrl[i]
                : "http://" + splitAroundUrl[i];
            if (i % 2 && !selectionIsInsideALink) {
                this.dependencies.dom.insert(
                    this.dependencies.link.createLink(url, splitAroundUrl[i]),
                );
            } else if (splitAroundUrl[i] !== "") {
                this.dependencies.clipboard.pasteText(splitAroundUrl[i]);
            }
        }
    }

    /**
     * @param {EditorSelection} selection
     */
    selectFullySelectedLink(selection) {
        const link = closestElement(selection.anchorNode, "a");
        if (
            link?.parentElement?.isContentEditable &&
            cleanZWChars(selection.textContent()) === cleanZWChars(link.innerText) &&
            !this.getResource("unremovable_node_predicates").some((p) => p(link))
        ) {
            this.dependencies.selection.setSelection({
                anchorNode: link.parentElement,
                anchorOffset: childNodeIndex(link) + (selection.direction ? 0 : 1),
                focusNode: link.parentElement,
                focusOffset: childNodeIndex(link) + (selection.direction ? 1 : 0),
            });
        }
    }
}
