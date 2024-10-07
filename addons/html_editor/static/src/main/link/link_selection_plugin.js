import { Plugin } from "@html_editor/plugin";
import { closestElement, descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { cleanTextNode, removeClass } from "@html_editor/utils/dom";
import { prepareUpdate } from "@html_editor/utils/dom_state";
import { leftPos } from "@html_editor/utils/position";
import { isProtected, isProtecting, isZwnbsp } from "@html_editor/utils/dom_info";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

function isLegitZwnbsp(textNode) {
    // Content must much exactly one ZWNBSP character.
    if (textNode.textContent !== "\ufeff") {
        return false;
    }
    // Leading and trailing ZWNBSP external to a link are legit.
    if (textNode.nextSibling?.nodeName === "A" || textNode.previousSibling?.nodeName === "A") {
        return true;
    }
    if (textNode.parentNode.nodeName !== "A") {
        return false;
    }
    // Leading and trailing ZWNBSP internal to a link are legit.
    if (textNode.parentNode.firstChild === textNode || textNode.parentNode.lastChild === textNode) {
        return true;
    }
    return false;
}

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
    static dependencies = ["selection"];
    // TODO ABD: refactor to handle Knowledge comments inside this plugin without sharing padLinkWithZwnbsp.
    static shared = ["padLinkWithZwnbsp"];
    resources = {
        mutation_filtered_classes: ["o_link_in_selection"],
        link_ignore_classes: ["o_link_in_selection"],
        onSelectionChange: this.resetLinkInSelection.bind(this),
        arrows_should_skip: (ev, char, lastSkipped) =>
            // Skip first FEFF, but not the second one (unless shift is pressed).
            char === "\uFEFF" && (ev.shiftKey || lastSkipped !== "\uFEFF"),
    };

    handleCommand(command, payload) {
        switch (command) {
            case "NORMALIZE":
                this.normalize(payload.node || this.editable);
                break;
            case "CLEAN_FOR_SAVE":
                this.cleanForSave(payload);
                break;
            case "CLEAN":
                this.removeFEFFs(payload.root, { preserveSelection: true });
                break;
        }
    }

    /**
     * @param {Element} root
     */
    normalize(root) {
        this.updateFEFFs(root);
        this.resetLinkInSelection();
    }

    /**
     * @param {Element} root
     */
    cleanForSave({ root, preserveSelection = false }) {
        this.removeFEFFs(root, { preserveSelection });
        this.clearLinkInSelectionClass(root);
    }

    /**
     * @param {Element} root
     */
    updateFEFFs(root) {
        this.removeFEFFs(root, { exclude: isLegitZwnbsp });

        for (const link of selectElements(root, "a")) {
            if (this.isLinkEligibleForZwnbsp(link)) {
                // Only add the ZWNBSP for simple (possibly styled) text links, and
                // never in a nav.
                this.padLinkWithZwnbsp(link);
            }
        }
    }

    /**
     * Removes ZWNBSP characters from text nodes within the given root.
     *
     * @param {Element} root
     * @param {Object} [options]
     * @param {Function} [options.exclude]
     */
    removeFEFFs(root, { exclude = () => false, preserveSelection = true } = {}) {
        const defaultFilter = (node) =>
            node.nodeType === Node.TEXT_NODE &&
            node.textContent.includes("\uFEFF") &&
            node.parentElement.isContentEditable;

        const combinedFilter = (node) => defaultFilter(node) && !exclude(node);
        const nodes = descendants(root).filter(combinedFilter);
        if (nodes.length > 0) {
            const cursors = preserveSelection ? this.shared.preserveSelection() : null;
            for (const node of nodes) {
                // Remove all FEFF within a `prepareUpdate` to make sure to make <br>
                // nodes visible if needed.
                const restoreSpaces = prepareUpdate(...leftPos(node));
                cleanTextNode(node, "\uFEFF", cursors);
                restoreSpaces();
            }
            cursors?.restore();
        }

        // Comment in the original code:
        //   We replace the text node with a new text node with the
        //   update text rather than just changing the text content of
        //   the node because these two methods create different
        //   mutations and at least the tour system breaks if all we
        //   send here is a text content change.
        // This is not done here as it breaks other plugins that rely on the
        // reference to the text node.
    }

    /**
     * Take a link and pad it with non-break zero-width spaces to ensure that it
     * is always possible to place the cursor at its inner and outer edges.
     *
     * @param {HTMLAnchorElement} link
     */
    padLinkWithZwnbsp(link) {
        const cursors = this.shared.preserveSelection();
        if (!isZwnbsp(link.firstChild)) {
            cursors.shiftOffset(link, 1);
            link.prepend(this.document.createTextNode("\uFEFF"));
        }
        if (!isZwnbsp(link.lastChild)) {
            link.append(this.document.createTextNode("\uFEFF"));
        }
        if (!isZwnbsp(link.previousSibling)) {
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

    isLinkEligibleForZwnbsp(link) {
        return (
            link.isContentEditable &&
            this.editable.contains(link) &&
            !isProtected(link) &&
            !isProtecting(link) &&
            !this.getResource("excludeLinkZwnbsp").some((callback) => callback(link))
        );
    }

    isLinkEligibleForVisualIndication(link) {
        return (
            this.isLinkEligibleForZwnbsp(link) &&
            !this.getResource("excludeLinkVisualIndication").some((callback) => callback(link))
        );
    }

    /**
     * Apply the o_link_in_selection class if the selection is in a single link,
     * remove it otherwise.
     *
     * @param {SelectionData} [selectionData]
     */
    resetLinkInSelection(selectionData = this.shared.getSelectionData()) {
        this.clearLinkInSelectionClass(this.editable);

        const { anchorNode, focusNode } = selectionData.editableSelection;
        const [anchorLink, focusLink] = [anchorNode, focusNode].map((node) =>
            closestElement(node, "a")
        );
        const singleLinkInSelection = anchorLink === focusLink && anchorLink;

        if (
            singleLinkInSelection &&
            this.isLinkEligibleForVisualIndication(singleLinkInSelection)
        ) {
            singleLinkInSelection.classList.add("o_link_in_selection");
        }
    }

    clearLinkInSelectionClass(root) {
        for (const link of selectElements(root, ".o_link_in_selection")) {
            removeClass(link, "o_link_in_selection");
        }
    }
}
