import { Plugin } from "@html_editor/plugin";
import { cleanEmptyAncestors, cleanTextNode } from "@html_editor/utils/dom";
import { isElement, isEmptyTextNode, isTextNode, isZwnbsp } from "@html_editor/utils/dom_info";
import { prepareUpdate } from "@html_editor/utils/dom_state";
import {
    childNodes,
    closestElement,
    descendants,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import { leftPos, rightPos } from "@html_editor/utils/position";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { withSequence } from "../utils/resource";

/** @typedef {import("../core/selection_plugin").Cursors} Cursors */

/**
 * @typedef { Object } FeffShared
 * @property { FeffPlugin['addFeff'] } addFeff
 * @property { FeffPlugin['removeFeffs'] } removeFeffs
 * @property { FeffPlugin['surroundWithFeffs'] } surroundWithFeffs
 * @property { FeffPlugin['updateFeffs'] } updateFeffs
 */

/**
 * @typedef {((node: Node) => boolean | undefined)[]} would_feff_be_legit_predicates
 * @typedef {((root: EditorContext["editable"], cursors: Cursors) => Node[])[]} feff_providers
 * @typedef {(() => string)[]} selectors_for_feff_providers
 */

/**
 * This plugin manages the insertion and removal of the zero-width no-break
 * space character (U+FEFF). These characters enable the user to place the
 * cursor in positions that would otherwise not be easy or possible, such as
 * between two contenteditable=false elements, or at the end (but inside) of a
 * link.
 */
export class FeffPlugin extends Plugin {
    static id = "feff";
    static dependencies = ["selection"];
    static shared = ["addFeff", "removeFeffs", "surroundWithFeffs", "updateFeffs"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        normalize_processors: withSequence(Infinity, this.updateFeffs.bind(this)),
        // Must be after link selection plugin's clean for save
        clean_for_save_processors: withSequence(20, this.cleanForSave.bind(this)),
        on_will_merge_adjacent_siblings_handlers:
            this.onWillMergeAdjacentSiblingsHandler.bind(this),
        on_merged_adjacent_siblings_handlers: this.onMergedAdjacentSiblingsHandler.bind(this),
        is_char_tangible_for_keyboard_navigation_predicates: (ev, char, lastSkipped) => {
            // Skip first FEFF, but not the second one (unless shift is pressed).
            if (char === "\uFEFF" && (ev.shiftKey || lastSkipped !== "\uFEFF")) {
                return false;
            }
        },
        clipboard_content_processors: this.processContentForClipboard.bind(this),
        clipboard_text_processors: (text) => text.replace(/\ufeff/g, ""),
        would_feff_be_legit_predicates: (node) => {
            const previousSibling = node.previousSibling;
            const nextSibling = node.nextSibling;
            if (this.hasFeff(previousSibling) || this.hasFeff(nextSibling)) {
                return false;
            } else {
                if (
                    closestElement(previousSibling)?.matches(this.feffProvidersSelector) ||
                    closestElement(nextSibling)?.matches(this.feffProvidersSelector)
                ) {
                    return true;
                }
            }
        },
    };

    setup() {
        this.feffProvidersSelector = this.getResource("selectors_for_feff_providers")
            .map((provider) => provider())
            .join(", ");
    }

    cleanForSave(root, { preserveSelection = false } = {}) {
        if (preserveSelection) {
            const cursors = this.getCursors();
            this.removeFeffs(root, cursors, { excludeLegit: false });
            cursors.restore();
        } else {
            this.removeFeffs(root, null, { excludeLegit: false });
        }
        return root;
    }

    onWillMergeAdjacentSiblingsHandler(root) {
        const cursors = this.getCursors();
        this.removeFeffs(root, cursors);
        cursors.restore();
    }
    onMergedAdjacentSiblingsHandler(root) {
        this.updateFeffs(root);
    }

    hasFeff(node) {
        return isTextNode(node) && node.textContent.includes("\ufeff");
    }

    /**
     * @param {Element} root
     * @param {Cursors} [cursors]
     * @param {Object} [options]
     * @param {(node: Node) => boolean} [options.exclude] the FEFFs to keep, by
     * default the ones of the focused link
     */
    removeFeffs(
        root,
        cursors,
        {
            exclude = (node) => closestElement(node, "a.o_link_in_selection"),
            excludeLegit = true,
        } = {}
    ) {
        if (excludeLegit) {
            const excludeParam = exclude;
            exclude = (node) =>
                excludeParam?.(node) ||
                (this.checkPredicates("would_feff_be_legit_predicates", node) ?? false);
        }
        const isEditable = (node) => node.parentElement.isContentEditable;
        const composedFilter = (node) => this.hasFeff(node) && isEditable(node) && !exclude(node);

        for (const node of descendants(root).filter(composedFilter)) {
            // Remove all FEFF within a `prepareUpdate` to make sure to make <br>
            // nodes visible if needed.
            const restoreSpaces = prepareUpdate(...leftPos(node), ...rightPos(node));
            const parent = node.parentNode;
            cleanTextNode(node, "\ufeff", cursors);
            cleanEmptyAncestors(
                parent,
                cursors,
                (node) =>
                    node.hasAttribute("data-oe-zws-empty-inline") ||
                    !(this.checkPredicates("is_node_removable_predicates", node) ?? true)
            );
            restoreSpaces();
        }
    }

    /**
     * @param {Element} element
     * @param {'before'|'after'|'prepend'|'append'} position
     * @param {Cursors} [cursors]
     * @returns {Node}
     */
    addFeff(element, position, cursors) {
        const feff = this.document.createTextNode("\ufeff");
        cursors?.update(callbacksForCursorUpdate[position](element, feff));
        element[position](feff);
        return feff;
    }

    /**
     * Returns the element that gets the inner FEFF of the given element, at the
     * start or at the end of its content: the deepest splittable inline element
     * holding this edge.
     *
     * Such an element emptied of its text gets a zero-width space, as the other
     * empty inlines do, so that it is removed on save if no text is typed in it.
     *
     * @param {Element} element
     * @param {0|-1} index 0 for the start of the content, -1 for its end
     * @returns {Element}
     */
    getInnerFeffContainer(element, index) {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        // Skip the FEFFs, the empty text nodes, and the nodes holding only
        // FEFFs unless the selection is in them.
        const getContentNodes = (parent) =>
            childNodes(parent).filter(
                (node) =>
                    !isZwnbsp(node) &&
                    !isEmptyTextNode(node) &&
                    (!/^\ufeff+$/.test(node.textContent) || node.contains(anchorNode))
            );
        let container = element;
        let edgeNode = getContentNodes(container).at(index);
        while (
            isElement(edgeNode) &&
            edgeNode.hasChildNodes() &&
            // Not in unsplittable elements (e.g. non-editable elements, QWeb
            // directives), nor in the empty inlines waiting for text.
            (this.checkPredicates("is_node_splittable_predicates", edgeNode) ?? true) &&
            !edgeNode.matches("[data-oe-zws-empty-inline]")
        ) {
            const innerEdgeNode = getContentNodes(edgeNode).at(index);
            if (!innerEdgeNode) {
                edgeNode.append(this.document.createTextNode("\u200B"));
                edgeNode.setAttribute("data-oe-zws-empty-inline", "");
                break;
            }
            container = edgeNode;
            edgeNode = innerEdgeNode;
        }
        return container;
    }

    /**
     * Adds FEFFs around the node and at the inner edges of its content.
     *
     * @param {Element} node
     * @param {Cursors} [cursors]
     * @returns {Node[]}
     */
    surroundWithFeffs(node, cursors) {
        const addFeff = (element, position) => {
            // skip cursor update for append, we want to keep it before
            // the added FEFF
            const c = position === "append" ? null : cursors;
            return this.addFeff(element, position, c);
        };

        const zwnbspNodes = [];
        for (const [element, position, relation] of [
            [node, "before", "previousSibling"],
            [node, "after", "nextSibling"],
            [this.getInnerFeffContainer(node, 0), "prepend", "firstChild"],
            [this.getInnerFeffContainer(node, -1), "append", "lastChild"],
        ]) {
            const candidate = element[relation];
            const feff =
                isZwnbsp(candidate) && !zwnbspNodes.includes(candidate)
                    ? candidate
                    : addFeff(element, position);
            zwnbspNodes.push(feff);
        }
        return zwnbspNodes;
    }

    /**
     * Adds a FEFF before and after each element that matches the selectors
     * provided by the registered providers.
     *
     * @param {Element} root
     * @param {Cursors} cursors
     * @returns {Node[]}
     */
    padWithFeffs(root, cursors) {
        if (!this.feffProvidersSelector) {
            return [];
        }
        const elements = selectElements(root, this.feffProvidersSelector);
        const isEditable = (node) => node.parentElement?.isContentEditable;
        const feffNodes = elements
            .filter(isEditable)
            .flatMap((el) => {
                const addFeff = (position) => this.addFeff(el, position, cursors);
                return [
                    isZwnbsp(el.previousSibling) ? el.previousSibling : addFeff("before"),
                    isZwnbsp(el.nextSibling) ? el.nextSibling : addFeff("after"),
                ];
            })
            // Avoid sequential FEFFs
            .filter((feff, i, array) => !(i > 0 && areCloseSiblings(array[i - 1], feff)));
        return feffNodes;
    }

    updateFeffs(root) {
        const cursors = this.getCursors();
        // Pad based on selectors
        const feffNodesBasedOnSelectors = this.padWithFeffs(root, cursors);
        // Custom feff adding
        // Each provider is responsible for adding (or keeping) FEFF nodes and
        // returning a list of them.
        const customFeffNodes = this.getResource("feff_providers").flatMap((p) => p(root, cursors));
        const feffNodesToKeep = new Set([...feffNodesBasedOnSelectors, ...customFeffNodes]);
        this.removeFeffs(root, cursors, {
            exclude: (node) => feffNodesToKeep.has(node),
        });
        cursors.restore();
        return root;
    }

    /**
     * Retuns a patched version of cursors in which `restore` does nothing
     * unless `update` has been called at least once.
     */
    getCursors() {
        const cursors = this.dependencies.selection.preserveSelection();
        const originalUpdate = cursors.update.bind(cursors);
        const originalRestore = cursors.restore.bind(cursors);
        let shouldRestore = false;
        cursors.update = (...args) => {
            shouldRestore = true;
            return originalUpdate(...args);
        };
        cursors.restore = () => {
            if (shouldRestore) {
                originalRestore();
            }
        };
        return cursors;
    }

    processContentForClipboard(clonedContent) {
        descendants(clonedContent)
            .filter(isTextNode)
            .filter((node) => node.textContent.includes("\ufeff"))
            .forEach((node) => (node.textContent = node.textContent.replace(/\ufeff/g, "")));
        return clonedContent;
    }
}

/**
 * Whether two nodes are consecutive siblings, ignoring empty text nodes between
 * them.
 *
 * @param {Node} a
 * @param {Node} b
 */
function areCloseSiblings(a, b) {
    let next = a.nextSibling;
    // skip empty text nodes
    while (next && isTextNode(next) && !next.textContent) {
        next = next.nextSibling;
    }
    return next === b;
}
