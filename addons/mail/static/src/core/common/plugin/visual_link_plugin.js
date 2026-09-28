import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { isProtecting } from "@html_editor/utils/dom_info";
import { urlRegexp } from "@mail/utils/common/format";

const HIGHLIGHT_NAME = "o-mail-VisualLink";

/**
 * Styles the URLs of the composer as links, as they will be once posted.
 *
 * The styling uses the CSS Custom Highlight API and leaves the DOM untouched:
 * no link is created, so neither the history nor the saved content change.
 * It is updated on every content change, to stay in sync with `urlRegexp`.
 */
export class VisualLinkPlugin extends Plugin {
    static id = "visualLink";
    /** @type {import("plugins").EditorResources} */
    resources = {
        on_pending_mutations_staged_handlers: this.updateVisualLinks.bind(this),
        on_content_updated_handlers: this.updateVisualLinks.bind(this),
    };

    setup() {
        const highlights = this.window.CSS?.highlights;
        if (!highlights) {
            return;
        }
        // Shared by all the editors of the document, each one only manages its own ranges.
        this.highlight = highlights.get(HIGHLIGHT_NAME);
        if (!this.highlight) {
            this.highlight = new this.window.Highlight();
            highlights.set(HIGHLIGHT_NAME, this.highlight);
        }
        /** @type {Range[]} */
        this.ranges = [];
        this.updateVisualLinks();
    }

    destroy() {
        super.destroy();
        this.clearVisualLinks();
    }

    clearVisualLinks() {
        for (const range of this.ranges ?? []) {
            this.highlight.delete(range);
        }
        this.ranges = [];
    }

    updateVisualLinks() {
        if (!this.highlight) {
            return;
        }
        this.clearVisualLinks();
        for (const range of this.getUrlRanges()) {
            this.highlight.add(range);
            this.ranges.push(range);
        }
    }

    /** @returns {Range[]} */
    getUrlRanges() {
        const content = { text: "", textNodes: [] };
        this.collectText(this.editable, content);
        const ranges = [];
        for (const match of content.text.matchAll(urlRegexp)) {
            const url = match[0];
            if (!URL.canParse(/^https?:\/\//i.test(url) ? url : `http://${url}`)) {
                continue;
            }
            const start = content.textNodes.find(
                ({ node, offset }) =>
                    offset <= match.index && match.index < offset + node.textContent.length
            );
            const endIndex = match.index + url.length;
            const end = content.textNodes.find(
                ({ node, offset }) =>
                    offset < endIndex && endIndex <= offset + node.textContent.length
            );
            const range = this.document.createRange();
            range.setStart(start.node, match.index - start.offset);
            range.setEnd(end.node, endIndex - end.offset);
            ranges.push(range);
        }
        return ranges;
    }

    /**
     * Collects the text of the editable, so that URLs can be matched in it.
     *
     * Each text node's position in the collected text is kept, to map matches
     * back to the DOM. Line breaks, blocks, mentions, links and protected nodes
     * are collected as a space, so that a URL stops there without including its
     * trailing punctuation, as when the message is linkified on post.
     *
     * @param {Node} root
     * @param {{ text: string, textNodes: { node: Text, offset: number }[] }} content
     */
    collectText(root, content) {
        for (const node of root.childNodes) {
            if (node.nodeType === Node.TEXT_NODE) {
                content.textNodes.push({ node, offset: content.text.length });
                content.text += node.textContent;
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                if (node.matches("a, [contenteditable='false']") || isProtecting(node)) {
                    content.text += " ";
                    continue;
                }
                const isSeparator = node.nodeName === "BR" || isBlock(node);
                if (isSeparator) {
                    content.text += " ";
                }
                this.collectText(node, content);
                if (isSeparator) {
                    content.text += " ";
                }
            }
        }
    }
}
