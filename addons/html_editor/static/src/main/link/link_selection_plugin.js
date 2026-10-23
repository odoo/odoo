import { Plugin } from "@html_editor/plugin";
import { childNodes, closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { removeClass } from "@html_editor/utils/dom";
import {
    isEmptyTextNode,
    isProtected,
    isProtecting,
    isZwnbsp,
    PROTECTED_QWEB_SELECTOR,
} from "@html_editor/utils/dom_info";

/*
    This plugin solves selection issues around links (allowing the cursor at the
    inner and outer edges of links).

    Every link receives 4 zero-width non-breaking spaces (unicode FEFF
    characters, hereafter referred to as ZWNBSP):
    - one before the link
    - one before the first leaf of the link
    - one after the last leaf of the link
    - one after the link
    like so: `//ZWNBSP//<a>//ZWNBSP//label//ZWNBSP//</a>//ZWNBSP`.
    The inner ones go inside the formats of the label, like so:
    `<a><s>//ZWNBSP//label//ZWNBSP//</s></a>`, so that text typed at the inner
    edges of the link keeps them.

    A visual indication ( `o_link_in_selection` class) is added to a link when
    the selection is contained within it.

    This is not applied in the following cases:

    - in a navbar (since its links are managed via the snippets system, not
    via pure edition) and, similarly, in .nav-link links
    - in links that have content more complex than simple text
    - on non-editable links or links that are not within the editable area
 */

/**
 * @typedef { Object } LinkSelectionShared
 * @property { LinkSelectionPlugin['padLinkWithZwnbsp'] } padLinkWithZwnbsp
 */

export class LinkSelectionPlugin extends Plugin {
    static id = "linkSelection";
    static dependencies = ["selection", "feff"];
    // TODO ABD: refactor to handle Knowledge comments inside this plugin without sharing padLinkWithZwnbsp.
    static shared = ["padLinkWithZwnbsp"];
    resources = {
        /** Handlers */
        selectionchange_handlers: this.resetLinkInSelection.bind(this),
        clean_for_save_handlers: ({ root }) => this.clearLinkInSelectionClass(root),
        normalize_handlers: (root) => {
            this.updateLinkFeffs(root);
            this.resetLinkInSelection();
        },
        feff_providers: this.addFeffsToLinks.bind(this),
        system_classes: ["o_link_in_selection"],
    };

    /**
     * Updates the FEFFs of the whole link holding the root, as the inner FEFFs
     * of a previous update can be outside the root, in the label.
     *
     * @param {Element} root
     */
    updateLinkFeffs(root) {
        const link = closestElement(root, "a");
        if (link && link !== root) {
            this.dependencies.feff.updateFeffs(link);
        }
    }

    addFeffsToLinks(root, cursors) {
        // The inner FEFFs of the link holding the root can be in the root.
        return [...selectElements(closestElement(root, "a") || root, "a")]
            .filter(this.isLinkEligibleForZwnbsp.bind(this))
            .flatMap((link) => this.addFeffs(link, cursors));
    }

    addFeffs(link, cursors) {
        const addFeff = (element, position) => {
            // skip cursor update for append, we want to keep it before the added FEFF
            const c = position === "append" ? null : cursors;
            return this.dependencies.feff.addFeff(element, position, c);
        };

        const zwnbspNodes = [];
        const [startParent, endParent] = getInnerFeffParents(link);
        for (const [element, position, relation] of [
            [link, "before", "previousSibling"],
            [link, "after", "nextSibling"],
            [startParent, "prepend", "firstChild"],
            [endParent, "append", "lastChild"],
        ]) {
            const candidate = element[relation];
            const feff = isZwnbsp(candidate) ? candidate : addFeff(element, position);
            zwnbspNodes.push(feff);
        }
        return zwnbspNodes;
    }

    /**
     * Take a link and pad it with non-break zero-width spaces to ensure that it
     * is always possible to place the cursor at its inner and outer edges.
     *
     * @param {HTMLAnchorElement} link
     */
    padLinkWithZwnbsp(link) {
        const cursors = this.dependencies.selection.preserveSelection();
        this.addFeffs(link, cursors);
        cursors.restore();
    }

    isLinkEligibleForZwnbsp(link) {
        return (
            link.isContentEditable &&
            link.parentElement.isContentEditable &&
            this.editable.contains(link) &&
            !isProtected(link) &&
            !isProtecting(link) &&
            !this.getResource("ineligible_link_for_zwnbsp_predicates").some((p) => p(link))
        );
    }

    isLinkEligibleForVisualIndication(link) {
        return (
            this.isLinkEligibleForZwnbsp(link) &&
            !this.getResource("ineligible_link_for_selection_indication_predicates").some(
                (predicate) => predicate(link)
            )
        );
    }

    /**
     * Apply the o_link_in_selection class if the selection is in a single link,
     * remove it otherwise.
     *
     * @param {SelectionData} [selectionData]
     */
    resetLinkInSelection(selectionData = this.dependencies.selection.getSelectionData()) {
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

    /**
     * ============================================================= *
     * The methods below are kept for compatibility (stable policy). *
     * To be removed in master.                                      *
     * ============================================================= *
     */

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
        this.dependencies.feff.updateFeffs(root);
    }

    /**
     * Removes ZWNBSP characters from text nodes within the given root.
     *
     * @param {Element} root
     * @param {Object} [options]
     * @param {Function} [options.exclude]
     */
    removeFEFFs(root, { exclude = () => false, preserveSelection = true } = {}) {
        const cursors = preserveSelection ? this.dependencies.selection.preserveSelection() : null;
        this.dependencies.feff.removeFeffs(root, cursors, { exclude });
        cursors?.restore();
    }
}

/**
 * Returns the parents of the inner FEFFs of the link, at the start and at the
 * end of its label: the deepest editable inline elements holding these edges.
 *
 * Such an element emptied of its text gets a zero-width space, as the other
 * empty inlines do, so that it is removed on save if no text is typed in it.
 *
 * @param {HTMLAnchorElement} link
 * @returns {Element[]}
 */
function getInnerFeffParents(link) {
    // Skip the FEFFs and the empty text nodes they leave once removed.
    const getContentNodes = (element) =>
        childNodes(element).filter((node) => !isZwnbsp(node) && !isEmptyTextNode(node));
    const getInnerFeffParent = (index) => {
        let parent = link;
        let edgeNode = getContentNodes(parent).at(index);
        while (
            edgeNode?.nodeType === Node.ELEMENT_NODE &&
            edgeNode.isContentEditable &&
            edgeNode.hasChildNodes() &&
            // Not in QWeb directives, nor in the empty inlines waiting for text.
            !edgeNode.matches(`t, ${PROTECTED_QWEB_SELECTOR}, [data-oe-zws-empty-inline]`)
        ) {
            const innerEdgeNode = getContentNodes(edgeNode).at(index);
            if (!innerEdgeNode) {
                edgeNode.append(edgeNode.ownerDocument.createTextNode("\u200B"));
                edgeNode.setAttribute("data-oe-zws-empty-inline", "");
                break;
            }
            parent = edgeNode;
            edgeNode = innerEdgeNode;
        }
        return parent;
    };
    // At the first and at the last content node of the label.
    return [getInnerFeffParent(0), getInnerFeffParent(-1)];
}
