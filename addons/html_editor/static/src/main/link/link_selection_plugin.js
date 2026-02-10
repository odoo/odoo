import { Plugin } from "@html_editor/plugin";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { removeClass } from "@html_editor/utils/dom";
import { isProtected, isProtecting } from "@html_editor/utils/dom_info";

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

/**
 * @typedef { Object } LinkSelectionShared
 * @property { LinkSelectionPlugin['padLinkWithZwnbsp'] } padLinkWithZwnbsp
 */

/**
 * @typedef {((link: HTMLLinkElement) => boolean)[]} ineligible_link_for_selection_indication_predicates
 * @typedef {((link: HTMLLinkElement) => boolean)[]} ineligible_link_for_zwnbsp_predicates
 */

export class LinkSelectionPlugin extends Plugin {
    static id = "linkSelection";
    static dependencies = ["selection", "feff"];
    // TODO ABD: refactor to handle Knowledge comments inside this plugin without sharing padLinkWithZwnbsp.
    static shared = ["padLinkWithZwnbsp"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        /** Handlers */
        selectionchange_handlers: this.resetLinkInSelection.bind(this),
        clean_for_save_handlers: ({ root }) => this.clearLinkInSelectionClass(root),
        normalize_handlers: () => this.resetLinkInSelection(),
        feff_providers: this.addFeffsToLinks.bind(this),
        system_classes: ["o_link_in_selection"],
        selection_placeholder_container_predicates: (container) => {
            if (container.nodeName === "BUTTON" || container.nodeName === "A") {
                // We sometimes have buttons or links that are blocks with
                // contenteditable=true but we never want to insert a paragraph
                // in them.
                // Note: this can be removed if `allowsParagraphRelatedElements`
                // is adapted to return false in these cases.
                return false;
            }
        },
    };

    addFeffsToLinks(root, cursors) {
        return [...selectElements(root, "a")]
            .filter(this.isLinkEligibleForZwnbsp.bind(this))
            .flatMap((link) => this.dependencies.feff.surroundWithFeffs(link, cursors));
    }

    /**
     * Take a link and pad it with non-break zero-width spaces to ensure that it
     * is always possible to place the cursor at its inner and outer edges.
     *
     * @param {HTMLAnchorElement} link
     */
    padLinkWithZwnbsp(link) {
        const cursors = this.dependencies.selection.preserveSelection();
        this.dependencies.feff.surroundWithFeffs(link, cursors);
        cursors.restore();
    }

    isLinkEligibleForZwnbsp(link) {
        const { anchorNode, focusNode } = this.dependencies.selection.getEditableSelection();
        // we can't rely on `o_link_in_selection` class because it can be
        // added to siblings while splitting link element.
        const isLinkSelected = link.contains(anchorNode) || link.contains(focusNode);
        const linkHasContentOrSelected =
            isLinkSelected || link.textContent.replaceAll("\ufeff", "");
        return (
            linkHasContentOrSelected &&
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
            this.isLinkEligibleForVisualIndication(singleLinkInSelection) &&
            this.document.activeElement === this.editable
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
