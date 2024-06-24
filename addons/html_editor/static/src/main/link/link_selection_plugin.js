import { Plugin } from "@html_editor/plugin";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { removeClass } from "@html_editor/utils/dom";
import { prepareUpdate } from "@html_editor/utils/dom_state";
import { leftPos, rightPos } from "@html_editor/utils/position";
import { isVisible } from "@html_editor/utils/dom_info";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

/*
    This plugin solves selection issues around links (allowing the cursor at the
    inner and outer edges of links).

    Every link receives 4 zero-width non-breaking spaces (unicode FEFF
    characters, hereafter referred to as ZWNBSP):
    - one before the link
    - one as the link's first child
    - one as the link's last child
    - one after the link
    like so: `//ZWNBSP//<a>//ZWNBSP//label//ZWNBSP//</a>//ZWNBSP`.

    A visual indication ( `o_link_in_selection` class) is added to a link when
    the selection is contained within it.

    This is not applied in the following cases:

    - in a navbar (since its links are managed via the snippets system, not
    via pure edition) and, similarly, in .nav-link links
    - in links that have content more complex than simple text
    - on non-editable links or links that are not within the editable area
 */
export class LinkSelectionPlugin extends Plugin {
    static name = "link_selection";
    static dependencies = ["selection", "split", "line_break"];
    /** @type { (p: LinkSelectionPlugin) => Record<string, any> } */
    static resources = (p) => ({
        history_rendering_classes: ["o_link_in_selection"],
        onSelectionChange: p.resetLinkInSelection.bind(p),
        split_element_block: { callback: p.handleSplitBlock.bind(p) },
        handle_insert_line_break_element: { callback: p.handleInsertLineBreak.bind(p) },
    });

    handleCommand(command, payload) {
        switch (command) {
            case "CLEAN":
                this.clean(payload.root);
                break;
            case "NORMALIZE":
                this.normalize(payload.root || this.editable);
                break;
        }
    }

    /**
     * Apply the o_link_in_selection class if the selection is in a single link,
     * remove it otherwise.
     *
     * @param {EditorSelection} [selection]
     */
    resetLinkInSelection(selection = this.shared.getEditableSelection()) {
        this.clearLinkInSelectionClass(this.editable);

        const { anchorNode, focusNode } = selection;
        const [anchorLink, focusLink] = [anchorNode, focusNode].map((node) =>
            closestElement(node, "a")
        );
        const singleLinkInSelection = anchorLink === focusLink && anchorLink;

        if (singleLinkInSelection && this.isLinkEligibleForZwnbsp(singleLinkInSelection)) {
            singleLinkInSelection.classList.add("o_link_in_selection");
        }
    }

    isLinkEligibleForZwnbsp(link) {
        return (
            link.isContentEditable &&
            this.editable.contains(link) &&
            !this.resources.blacklistLinkZwnbsp?.some((callback) => callback(link))
        );
    }

    // @todo: unify this and ZWSPlugin's cleanZWS into a single utility
    removeZWNBSPs(textNode, cursors) {
        const indexesToRemove = [...textNode.textContent.matchAll(/\uFEFF/g)].map(
            (match) => match.index
        );
        for (const index of indexesToRemove.toReversed()) {
            textNode.deleteData(index, 1);
        }
        cursors.update((cursor) => {
            if (cursor.node === textNode) {
                cursor.offset -= indexesToRemove.filter((i) => i < cursor.offset).length;
            }
        });
    }

    clearLinkInSelectionClass(root) {
        // @todo: maybe the querySelectorAll calls should include the root.
        for (const link of root.querySelectorAll(".o_link_in_selection")) {
            removeClass(link, "o_link_in_selection");
        }
    }

    clearFEFFs(root) {
        const cursors = this.shared.preserveSelection();
        let shouldRestoreCursors = false;
        for (const node of descendants(root)) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.includes("\uFEFF")) {
                // @todo: isn't rightPos needed as well?
                // Remove all FEFF within a `prepareUpdate` to make sure to make <br>
                // nodes visible if needed.
                const restore = prepareUpdate(...leftPos(node));
                this.removeZWNBSPs(node, cursors);
                shouldRestoreCursors = true;
                restore();
            }
        }
        if (shouldRestoreCursors) {
            cursors.restore();
        }
    }

    removeEmptyLinks(root) {
        // @todo: check for unremovables
        // @todo: preserve cursor and spaces
        for (const link of root.querySelectorAll("a")) {
            if (![...link.childNodes].some(isVisible) && !link.classList.length) {
                link.remove();
            }
        }
    }

    clean(root) {
        this.clearLinkInSelectionClass(root);
        this.clearFEFFs(root);
        this.removeEmptyLinks(root);
    }

    /**
     * Take a link and pad it with non-break zero-width spaces to ensure that it
     * is always possible to place the cursor at its inner and outer edges.
     *
     * @param {HTMLElement} editable
     * @param {HTMLAnchorElement} link
     */
    padLinkWithZws(link) {
        if (!this.isLinkEligibleForZwnbsp(link)) {
            // Only add the ZWNBSP for simple (possibly styled) text links, and
            // never in a nav.
            return;
        }
        const cursors = this.shared.preserveSelection();
        if (!link.textContent.startsWith("\uFEFF")) {
            cursors.shiftOffset(link, 1);
            link.prepend(this.document.createTextNode("\uFEFF"));
        }
        if (!link.textContent.endsWith("\uFEFF")) {
            // @todo: this changes the cursor, to preserve it we should simply
            // do nothing here.
            link.append(this.document.createTextNode("\uFEFF"));
        }
        if (!(link.previousSibling && link.previousSibling.textContent.endsWith("\uFEFF"))) {
            const nbzwsp = this.document.createTextNode("\uFEFF");
            cursors.update(callbacksForCursorUpdate.before(link, nbzwsp));
            link.before(nbzwsp);
        }
        if (!(link.nextSibling && link.nextSibling.textContent.startsWith("\uFEFF"))) {
            const nbzwsp = this.document.createTextNode("\uFEFF");
            cursors.update(callbacksForCursorUpdate.after(link, nbzwsp));
            link.after(nbzwsp);
        }
        cursors.restore();
    }

    normalize(root) {
        // @todo review the need for "root" parameter
        depthFirstPreOrderTraversal(root, (node) => this.updateZWNBSPs(node, root));
        this.resetLinkInSelection();
    }

    // @todo: ZWNBSPs are not removed in the case it is in the middle of link
    updateZWNBSPs(node, root) {
        if (node.nodeName === "A") {
            // Ensure links have ZWNBSPs so the selection can be set at their edges.
            this.padLinkWithZws(node);
        } else if (
            node.nodeType === Node.TEXT_NODE &&
            node.textContent.includes("\uFEFF") &&
            !closestElement(node, "a") &&
            // @todo review the need for "root" parameter
            // This apparently depends on the selection state. Should it?
            // Does it have to do with preserving cursor (avoid messing the selection)?
            !(
                closestElement(root, "[contenteditable=true]") &&
                this.shared.getTraversedNodes().includes(node)
            )
        ) {
            // Remove link ZWNBSP not in selection.
            const startsWithLegitZws =
                node.textContent.startsWith("\uFEFF") &&
                node.previousSibling &&
                node.previousSibling.nodeName === "A";
            const endsWithLegitZws =
                node.textContent.endsWith("\uFEFF") &&
                node.nextSibling &&
                node.nextSibling.nodeName === "A";
            let newText = node.textContent.replace(/\uFEFF/g, "");
            if (startsWithLegitZws) {
                newText = "\uFEFF" + newText;
            }
            if (endsWithLegitZws) {
                newText = newText + "\uFEFF";
            }
            if (newText !== node.textContent) {
                // We replace the text node with a new text node with the
                // update text rather than just changing the text content of
                // the node because these two methods create different
                // mutations and at least the tour system breaks if all we
                // send here is a text content change.
                const newTextNode = this.document.createTextNode(newText);
                node.before(newTextNode);
                node.remove();
                node = newTextNode;
            }
        }
    }

    /**
     * Special behavior for links: do not break the link at its edges, but
     * rather before/after it.
     *
     * @param {Object} params
     * @param {Element} params.targetNode
     * @param {number} params.targetOffset
     * @param {Element} params.blockToSplit
     */
    handleSplitBlock(params) {
        return this.handleEnterAtEdgeOfLink(params, this.shared.splitElementBlock);
    }

    /**
     * Special behavior for links: do not add a line break at its edges, but
     * rather outside it.
     *
     * @param {Object} params
     * @param {Element} params.targetNode
     * @param {number} params.targetOffset
     */
    handleInsertLineBreak(params) {
        return this.handleEnterAtEdgeOfLink(params, this.shared.insertLineBreakElement);
    }

    /**
     * @param {Object} params
     * @param {Element} params.targetNode
     * @param {number} params.targetOffset
     * @param {Element} [params.blockToSplit]
     * @param {Function} splitOrLineBreakCallback
     */
    handleEnterAtEdgeOfLink(params, splitOrLineBreakCallback) {
        // @todo: handle target Node being a descendent of a link (iterate over
        // leaves inside the link, rather than childNodes)
        let { targetNode, targetOffset } = params;
        if (targetNode.tagName !== "A") {
            return;
        }
        const edge = isAtEdgeofLink(targetNode, targetOffset);
        if (!edge) {
            return;
        }
        [targetNode, targetOffset] = edge === "start" ? leftPos(targetNode) : rightPos(targetNode);
        splitOrLineBreakCallback({ ...params, targetNode, targetOffset });
        return true;
    }
}

// @todo move this elsewhere, consider unifying with list's applyToTree
/**
 * @param {Node} root
 * @param {Function} callback
 */
function depthFirstPreOrderTraversal(root, callback) {
    callback(root);
    // Frozen childNodes list
    const childNodes = [...root.childNodes];
    for (const child of childNodes) {
        depthFirstPreOrderTraversal(child, callback);
    }
}

/**
 * @param { HTMLAnchorElement } link
 * @param {number} offset
 * @returns {"start"|"end"|false}
 */
function isAtEdgeofLink(link, offset) {
    const childNodes = [...link.childNodes];
    let firstVisibleIndex = childNodes.findIndex(isVisible);
    firstVisibleIndex = firstVisibleIndex === -1 ? 0 : firstVisibleIndex;
    if (offset <= firstVisibleIndex) {
        return "start";
    }
    let lastVisibleIndex = childNodes.reverse().findIndex(isVisible);
    lastVisibleIndex = lastVisibleIndex === -1 ? 0 : childNodes.length - lastVisibleIndex;
    if (offset >= lastVisibleIndex) {
        return "end";
    }
    return false;
}

/*
TODO:
- handle insertion of a link eligible for ZWNBSP (age's commit ajusts selection
    in the insert command)
- deletePlugin: account for ZWNBSP in (at least):
    - shouldSkip
    - isVisibleChar
    -Obs: consider changing implementation of findPreviousPosition to use selection.modify instead?
*/
