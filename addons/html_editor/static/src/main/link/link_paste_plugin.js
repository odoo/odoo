import { closestElement } from "@html_editor/utils/dom_traversal";
import { URL_REGEX } from "./utils";
import { isImageUrl } from "@html_editor/utils/url";
import { Plugin } from "@html_editor/plugin";
import { leftPos } from "@html_editor/utils/position";

export class LinkPastePlugin extends Plugin {
    static name = "link_paste";
    static dependencies = ["link", "clipboard", "selection", "dom"];
    /** @type { (p: LinkPastePlugin) => Record<string, any> } */
    static resources = (p) => ({
        before_paste: p.removeFullySelectedLink.bind(p),
        handle_paste_text: p.handlePasteText.bind(p),
    });

    setup() {
        this.resources["handle_paste_url"] = this.resources["handle_paste_url"] || [];
    }

    /**
     * @param {EditorSelection} selection
     * @param {string} text
     */
    handlePasteText(selection, text) {
        let splitAroundUrl;
        // todo: add placeholder plugin that prevent any other plugin
        // Avoid transforming dynamic placeholder pattern to url.
        if (!text.match(/\${.*}/gi)) {
            splitAroundUrl = text.split(URL_REGEX);
            // Remove 'http(s)://' capturing group from the result (indexes
            // 2, 5, 8, ...).
            splitAroundUrl = splitAroundUrl.filter((_, index) => (index + 1) % 3);
        }
        if (!splitAroundUrl || splitAroundUrl.length < 3) {
            // Let the default paste handle the text.
            return false;
        }
        if (splitAroundUrl.length === 3 && !splitAroundUrl[0] && !splitAroundUrl[2]) {
            // Pasted content is a single URL.
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
            this.handlePasteTextUrlInsideLink(text, url, selectionIsInsideALink);
            return;
        }
        const isHandled = this.resources["handle_paste_url"].some((handler) => handler(text, url));
        if (isHandled) {
            return;
        }
        this.shared.insertLink(url, text);
    }
    /**
     * @param {string} text
     * @param {string} url
     * @param {boolean} selectionIsInsideALink
     */
    handlePasteTextUrlInsideLink(text, url, selectionIsInsideALink) {
        // A url cannot be transformed inside an existing link.
        // An image can be embedded inside an existing link, a video cannot.
        if (selectionIsInsideALink) {
            if (isImageUrl(url)) {
                const img = this.document.createElement("IMG");
                img.setAttribute("src", url);
                this.shared.domInsert(img);
            } else {
                this.shared.domInsert(text);
            }
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
            // Even indexes will always be plain text, and odd indexes will always be URL.
            // A url cannot be transformed inside an existing link.
            if (i % 2 && !selectionIsInsideALink) {
                this.shared.domInsert(this.shared.createLink(url, splitAroundUrl[i]));
            } else if (splitAroundUrl[i] !== "") {
                this.shared.pasteText(selection, splitAroundUrl[i]);
            }
        }
    }

    /**
     * @param {EditorSelection} selection
     */
    removeFullySelectedLink(selection) {
        // Replace entire link if its label is fully selected.
        const link = closestElement(selection.anchorNode, "a");
        if (
            link &&
            selection.textContent.replace(/\u200B/g, "") === link.innerText.replace(/\u200B/g, "")
        ) {
            const start = leftPos(link);
            link.remove();
            // @doto @phoenix do we still want normalize:false?
            this.shared.setSelection({
                anchorNode: start[0],
                anchorOffset: start[1],
                normalize: false,
            });
        }
    }
}
