import { Plugin } from "../plugin";
import { prepareUpdate } from "../utils/dom_state";
import { boundariesOut, leftPos, rightPos } from "../utils/position";
import { descendants } from "../utils/dom_traversal";
import { cleanTextNode } from "@html_editor/utils/dom";

const allWhitespaceRegex = /^[\s\u200b]*$/;

export class ZwsPlugin extends Plugin {
    static name = "zws";
    static dependencies = ["selection", "split"];
    static shared = ["insertAndSelectZws"];
    static resources = (p) => ({
        arrows_should_skip: (ev, char, lastSkipped) => char === "\u200b",
    });

    handleCommand(command, payload) {
        switch (command) {
            case "CLEAN":
                // TODO @phoenix: evaluate if this should be cleanforsave instead
                this.clean(payload.root);
                break;
            case "NORMALIZE":
                this.normalize(payload.node);
                break;
        }
    }

    normalize(element) {
        if (!element) {
            return;
        }
        let elementToClean = [...element.querySelectorAll("[data-oe-zws-empty-inline]")];

        if (element.getAttribute("data-oe-zws-empty-inline") !== null) {
            elementToClean.push(element);
        }
        elementToClean = elementToClean.filter((el) => {
            return !allWhitespaceRegex.test(el.textContent);
        });
        for (const el of elementToClean) {
            this.cleanElement(el);
        }
    }
    clean(root) {
        for (const el of root.querySelectorAll("[data-oe-zws-empty-inline]")) {
            this.cleanElement(el);
        }
    }

    cleanElement(element) {
        delete element.dataset.oeZwsEmptyInline;
        if (!allWhitespaceRegex.test(element.textContent)) {
            // The element has some meaningful text. Remove the ZWS in it.
            this.cleanZWS(element);
            return;
        }
        // @todo phoenix: consider making the delete plugin export isUnremovable instead?
        if (this.resources.unremovables.some((predicate) => predicate(element))) {
            return;
        }
        if (element.classList.length) {
            // Original comment from web_editor:
            // We only remove the empty element if it has no class, to ensure we
            // don't break visual styles (in that case, its ZWS was kept to
            // ensure the cursor can be placed in it).
            return;
        }
        const restore = prepareUpdate(...leftPos(element), ...rightPos(element));
        element.remove();
        restore();
    }

    cleanZWS(element) {
        const textNodes = descendants(element).filter((node) => node.nodeType === Node.TEXT_NODE);
        const cursors = this.shared.preserveSelection();
        for (const node of textNodes) {
            cleanTextNode(node, "\u200B", cursors);
        }
        cursors.restore();
    }

    insertText(selection, content) {
        if (selection.anchorNode.nodeType === Node.TEXT_NODE) {
            selection = this.shared.setSelection(
                {
                    anchorNode: selection.anchorNode.parentElement,
                    anchorOffset: this.shared.splitTextNode(
                        selection.anchorNode,
                        selection.anchorOffset
                    ),
                },
                { normalize: false }
            );
        }

        const txt = this.document.createTextNode(content || "#");
        const restore = prepareUpdate(selection.anchorNode, selection.anchorOffset);
        selection.anchorNode.insertBefore(
            txt,
            selection.anchorNode.childNodes[selection.anchorOffset]
        );
        restore();
        const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesOut(txt);
        this.shared.setSelection(
            { anchorNode, anchorOffset, focusNode, focusOffset },
            { normalize: false }
        );
        return txt;
    }

    /**
     * Use the actual selection (assumed to be collapsed) and insert a
     * zero-width space at its anchor point. Then, select that zero-width
     * space.
     *
     * @returns {Node} the inserted zero-width space
     */
    insertAndSelectZws() {
        const selection = this.shared.getEditableSelection();
        const zws = this.insertText(selection, "\u200B");
        this.shared.splitTextNode(zws, selection.anchorOffset);
        return zws;
    }
}
