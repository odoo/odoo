import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { nextLeaf, previousLeaf, ZERO_WIDTH_CHARS } from "../utils/dom_info";
import { prepareUpdate } from "../utils/dom_state";
import { boundariesOut, leftPos, nodeSize, rightPos } from "../utils/position";
import { descendants } from "../utils/dom_traversal";
import { cleanTextNode } from "@html_editor/utils/dom";

const allWhitespaceRegex = /^[\s\u200b]*$/;

export class ZwsPlugin extends Plugin {
    static name = "zws";
    static dependencies = ["selection", "split"];
    static shared = ["insertAndSelectZws"];

    setup() {
        this.addDomListener(this.editable, "keydown", (ev) => {
            const hotkey = getActiveHotkey(ev);
            switch (hotkey) {
                case "arrowright":
                case "shift+arrowright":
                case "arrowleft":
                case "shift+arrowleft":
                    this.moveSelection(ev);
                    break;
            }
        });
    }

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

    // @todo: move me to another plugin (arrow keys plugin ?)
    // Consider always preventing default and handle arrows left and right
    // movements with selection.modify.
    moveSelection(ev) {
        const side = ev.key === "ArrowLeft" ? "previous" : "next";

        // @todo phoenix: in the original code, they check if it s a code element, and if it is, they add a zws before it.
        // If the selection is at the edge of a code element at the edge of its
        // parent, make sure there's a zws next to it, where the selection can
        // then be set.

        // Move selection if adjacent character is zero-width space.
        let didSkipFeff = false;
        let adjacentCharacter = this.getAdjacentCharacter(side);
        let previousSelection; // Is used to stop if `modify` doesn't move the selection.
        const hasSelectionChanged = (oldSelection = {}) => {
            const newSelection = this.shared.getEditableSelection();
            return (
                oldSelection.anchorNode !== newSelection.anchorNode ||
                oldSelection.anchorOffset !== newSelection.anchorOffset ||
                oldSelection.focusNode !== newSelection.focusNode ||
                oldSelection.focusOffset !== newSelection.focusOffset
            );
        };
        while (
            ZERO_WIDTH_CHARS.includes(adjacentCharacter) &&
            hasSelectionChanged(previousSelection)
        ) {
            previousSelection = this.shared.getEditableSelection();
            this.shared.modifySelection(
                ev.shiftKey ? "extend" : "move",
                side === "previous" ? "backward" : "forward",
                "character"
            );
            didSkipFeff = didSkipFeff || adjacentCharacter === "\ufeff";
            adjacentCharacter = this.getAdjacentCharacter(side);
        }

        if (didSkipFeff && !ev.shiftKey) {
            // If moving, just skip the zws then stop. Otherwise, do as if
            // they weren't there.
            ev.preventDefault();
            ev.stopPropagation();
        }
    }

    // @todo: same as above (move me somewhere else)
    // There is some duplicated logic with deletePlugin's findPreviousPostion.
    // Consider unifying them.
    getAdjacentCharacter(side) {
        let { focusNode, focusOffset } = this.shared.getEditableSelection();
        const originalBlock = closestBlock(focusNode);
        let adjacentCharacter;
        while (!adjacentCharacter && focusNode) {
            if (side === "previous") {
                // @todo: this might be wrong in the first time, as focus node might not be a leaf.
                adjacentCharacter = focusOffset > 0 && focusNode.textContent[focusOffset - 1];
            } else {
                adjacentCharacter = focusNode.textContent[focusOffset];
            }
            if (!adjacentCharacter) {
                if (side === "previous") {
                    focusNode = previousLeaf(focusNode, this.editable);
                    focusOffset = focusNode && nodeSize(focusNode);
                } else {
                    focusNode = nextLeaf(focusNode, this.editable);
                    focusOffset = 0;
                }
                const characterIndex = side === "previous" ? focusOffset - 1 : focusOffset;
                adjacentCharacter = focusNode && focusNode.textContent[characterIndex];
            }
        }
        return closestBlock(focusNode) === originalBlock ? adjacentCharacter : undefined;
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
