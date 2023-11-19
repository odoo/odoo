import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { nextLeaf, previousLeaf } from "../utils/dom_info";
import { prepareUpdate } from "../utils/dom_state";
import { closestElement, descendants } from "../utils/dom_traversal";
import { boundariesOut, nodeSize } from "../utils/position";

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
                    this.moveRight();
                    break;
                case "shift+arrowright":
                    this.moveRight(true);
                    break;
                case "arrowleft":
                    this.moveLeft();
                    break;
                case "shift+arrowleft":
                    this.moveLeft(true);
                    break;
            }
        });
    }

    handleCommand(command, payload) {
        switch (command) {
            case "CLEAN":
                this.clean(payload.root);
                break;
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
        element.remove();
    }

    cleanZWS(element) {
        const textNodes = descendants(element).filter((node) => node.nodeType === Node.TEXT_NODE);
        const cursors = this.shared.preserveSelection();
        for (const node of textNodes) {
            let zwsIndex = node.textContent.search("\u200B");
            while (zwsIndex !== -1) {
                node.deleteData(zwsIndex, 1);
                cursors.update((cursor) => {
                    if (cursor.node === node && cursor.offset > zwsIndex) {
                        cursor.offset -= 1;
                    }
                });
                zwsIndex = node.textContent.search("\u200B");
            }
        }
        cursors.restore();
    }

    moveRight(hasShift) {
        // todo @phoenix: before they call this.clean if hasShift. Maybe we should do the same ?
        let { anchorNode, anchorOffset, focusNode, focusOffset } =
            this.shared.getEditableSelection();
        // @todo phoenix: in the original code, they check if it s a code element, and if it is, they add a zws after it.
        // Find next character.
        let nextCharacter = focusNode.textContent[focusOffset];
        const nextNode = nextLeaf(focusNode, this.editable);
        if (!nextCharacter && nextNode && closestBlock(nextNode) === closestBlock(focusNode)) {
            focusNode = nextNode;
            focusOffset = 0;
            nextCharacter = focusNode.textContent[focusOffset];
        }
        // Move selection if next character is zero-width space
        if (
            nextCharacter === "\u200B" &&
            !focusNode.parentElement.hasAttribute("data-o-link-zws")
        ) {
            focusOffset += 1;
            let newFocusNode = focusNode;
            while (
                newFocusNode &&
                (!newFocusNode.textContent[focusOffset] ||
                    !closestElement(newFocusNode).isContentEditable)
            ) {
                newFocusNode = nextLeaf(newFocusNode);
                focusOffset = 0;
            }
            if (!focusOffset && closestBlock(focusNode) !== closestBlock(newFocusNode)) {
                newFocusNode = focusNode; // Do not move selection to next block.
                focusOffset = nodeSize(focusNode);
            }

            this.shared.setSelection({
                anchorNode: hasShift ? anchorNode : newFocusNode,
                anchorOffset: hasShift ? anchorOffset : focusOffset,
                focusNode: newFocusNode,
                focusOffset,
            });
        }
    }

    moveLeft(hasShift) {
        // todo @phoenix: before they call this.clean if hasShift. Maybe we should do the same ?

        let { anchorNode, anchorOffset, focusNode, focusOffset } =
            this.shared.getEditableSelection();

        // @todo phoenix: in the original code, they check if it s a code element, and if it is, they add a zws before it.
        // Find previous character.
        let previousCharacter = focusOffset > 0 && focusNode.textContent[focusOffset - 1];
        const previousNode = previousLeaf(focusNode, this.editable);
        if (
            !previousCharacter &&
            previousNode &&
            closestBlock(previousNode) === closestBlock(focusNode)
        ) {
            focusNode = previousNode;
            focusOffset = nodeSize(focusNode);
            previousCharacter = focusNode.textContent[focusOffset - 1];
        }
        // Move selection if previous character is zero-width space
        if (
            previousCharacter === "\u200B" &&
            !focusNode.parentElement.hasAttribute("data-o-link-zws")
        ) {
            focusOffset -= 1;
            while (focusNode && (focusOffset < 0 || !focusNode.textContent[focusOffset])) {
                focusNode = nextLeaf(focusNode);
                focusOffset = focusNode && nodeSize(focusNode);
            }
            this.shared.setSelection({
                anchorNode: hasShift ? anchorNode : focusNode,
                anchorOffset: hasShift ? anchorOffset : focusOffset,
                focusNode: focusNode,
                focusOffset,
            });
        }
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
     * Use the actual selection (assumed to be collapsed) and insert a zero-width space at
     * its anchor point. Then, select that zero-width space.
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
