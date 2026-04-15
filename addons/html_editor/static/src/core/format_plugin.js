import { prepareUpdate } from "@html_editor/utils/dom_state";
import { withSequence } from "@html_editor/utils/resource";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import { cleanTextNode, fillEmpty, removeClass, splitTextNode, unwrapContents } from "../utils/dom";
import {
    hasPseudoElementContent,
    hasSameClasses,
    hasSameStyleAttributes,
    hasVisibleContent,
    isContentEditable,
    isElement,
    isEmptyBlock,
    isEmptyTextNode,
    isPhrasingContent,
    isSelfClosingElement,
    isStylable,
    isTextNode,
    isVisible,
    isVisibleTextNode,
    isZwnbsp,
    isZWS,
    previousLeaf,
    PROTECTED_QWEB_SELECTOR,
} from "../utils/dom_info";
import { isFakeLineBreak } from "../utils/dom_state";
import {
    childNodes,
    closestElement,
    descendants,
    findFurthest,
    selectElements,
} from "../utils/dom_traversal";
import { formatsSpecs, FORMATTABLE_TAGS } from "../utils/formatting";
import { boundariesIn, boundariesOut, DIRECTIONS, leftPos, rightPos } from "../utils/position";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

const allWhitespaceRegex = /^[\s\u200b]*$/;
const NOT_A_NUMBER = /[^\d]/g;

function isFormatted(formatPlugin, format) {
    return (sel, nodes) => formatPlugin.isSelectionFormat(format, nodes);
}

/**
 * @typedef {Object} FormatShared
 * @property { FormatPlugin['isSelectionFormat'] } isSelectionFormat
 * @property { FormatPlugin['insertAndSelectZws'] } insertAndSelectZws
 * @property { FormatPlugin['mergeAdjacentInlines'] } mergeAdjacentInlines
 * @property { FormatPlugin['formatSelection'] } formatSelection
 */

/**
 * @typedef {((formatName: string, options: {
 *      formatProps: object,
 *      applyStyle: boolean,
 * }) => void | boolean)[]} format_selection_overrides
 * @typedef {(() => void)[]} on_all_formats_removed_handlers
 * @typedef {((root: Node) => void)[]} on_will_merge_adjacent_siblings_handlers
 * @typedef {((root: Node) => void)[]} on_merged_adjacent_siblings_handlers
 *
 * @typedef {((className: string) => boolean | undefined)[]} is_format_class_predicates
 * @typedef {((node: Node) => boolean | undefined)[]} has_format_predicates
 *
 * @typedef {(({
 *      node: Node,
 *      nodeStyle: CSSStyleProperties,
 *      node2: Node,
 *      node2Style: CSSStyleProperties,
 * }) => void | true)[]} are_similar_elements_overrides
 */

export class FormatPlugin extends Plugin {
    static id = "format";
    static dependencies = ["selection", "history", "input", "split", "delete"];
    // TODO ABD: refactor to handle Knowledge comments inside this plugin without sharing mergeAdjacentInlines.
    static shared = [
        "areSimilarElements",
        "isSelectionFormat",
        "insertAndSelectZws",
        "mergeAdjacentInlines",
        "formatSelection",
        "removeFormats",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "formatBold",
                description: _t("Toggle bold"),
                icon: "fa-bold",
                run: this.formatSelection.bind(this, "bold"),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "formatItalic",
                description: _t("Toggle italic"),
                icon: "fa-italic",
                run: this.formatSelection.bind(this, "italic"),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "formatUnderline",
                description: _t("Toggle underline"),
                icon: "fa-underline",
                run: this.formatSelection.bind(this, "underline"),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "formatStrikethrough",
                description: _t("Toggle strikethrough"),
                icon: "fa-strikethrough",
                run: this.formatSelection.bind(this, "strikeThrough"),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "formatFontSize",
                run: ({ size }) =>
                    this.formatSelection("fontSize", {
                        applyStyle: true,
                        formatProps: { size },
                    }),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "formatFontSizeClassName",
                run: ({ className }) =>
                    this.formatSelection("setFontSizeClassName", {
                        applyStyle: true,
                        formatProps: { className },
                    }),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "removeFormat",
                description: (sel, nodes) =>
                    nodes && this.hasAnyFormat(nodes)
                        ? _t("Remove Format")
                        : _t("Selection has no format"),
                icon: "fa-eraser",
                run: this.removeAllFormats.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        shortcuts: [
            { hotkey: "control+b", commandId: "formatBold" },
            { hotkey: "control+i", commandId: "formatItalic" },
            { hotkey: "control+u", commandId: "formatUnderline" },
            { hotkey: "control+5", commandId: "formatStrikethrough" },
            { hotkey: "control+space", commandId: "removeFormat" },
        ],
        toolbar_groups: withSequence(20, { id: "decoration" }),
        toolbar_items: [
            {
                id: "bold",
                description: _t("Bold (Ctrl + B)"),
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatBold",
                isActive: isFormatted(this, "bold"),
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
            },
            {
                id: "italic",
                description: _t("Italic (Ctrl + I)"),
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatItalic",
                isActive: isFormatted(this, "italic"),
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
            },
            {
                id: "underline",
                description: _t("Underline (Ctrl + U)"),
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatUnderline",
                isActive: isFormatted(this, "underline"),
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
            },
            {
                id: "strikethrough",
                description: _t("Strikethrough (Ctrl + 5)"),
                groupId: "decoration",
                commandId: "formatStrikethrough",
                isActive: isFormatted(this, "strikeThrough"),
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
            },
            withSequence(20, {
                id: "remove_format",
                groupId: "decoration",
                commandId: "removeFormat",
                isDisabled: (sel, nodes) =>
                    !this.hasAnyFormat(nodes) || nodes.some((node) => !isStylable(node)),
            }),
        ],
        /** Handlers */
        on_beforeinput_handlers: withSequence(20, this.onBeforeInput.bind(this)),
        on_selectionchange_handlers: this.removeEmptyInlineElement.bind(this),
        on_will_set_tag_handlers: this.removeFontSizeFormat.bind(this),
        before_insert_processors: this.unwrapEmptyFormat.bind(this),

        /** Processors */
        clean_for_save_processors: this.cleanForSave.bind(this),
        normalize_processors: this.normalize.bind(this),

        /** Predicates */
        is_char_tangible_for_keyboard_navigation_predicates: (_, char) => {
            if (char === "\u200b") {
                return false;
            }
        },
    };

    /**
     * @param {string[]} formats
     * @param {Node[]} targetedNodes
     */
    removeFormats(formats, targetedNodes) {
        const editableTargetedNodes = targetedNodes.filter(
            this.dependencies.selection.isNodeEditable
        );
        for (const format of formats) {
            if (
                !formatsSpecs[format].removeStyle ||
                !this.hasSelectionFormat(format, editableTargetedNodes)
            ) {
                continue;
            }
            this.formatSelection(format, { applyStyle: false, removeFormat: true });
        }
    }

    unwrapEmptyFormat(insertedNode) {
        const anchorNode = this.dependencies.selection.getEditableSelection().anchorNode;
        if (!allWhitespaceRegex.test(insertedNode.textContent)) {
            return insertedNode;
        }
        const emptyZWS = closestElement(anchorNode, "[data-oe-zws-empty-inline]");
        if (
            !emptyZWS ||
            !emptyZWS.parentElement.isContentEditable ||
            this.dependencies.delete.isUnremovable(emptyZWS)
        ) {
            return insertedNode;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        cursors.update(callbacksForCursorUpdate.remove(emptyZWS));
        emptyZWS.remove();
        cursors.restore();
        return insertedNode;
    }

    removeAllFormats() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        this.removeFormats(Object.keys(formatsSpecs), targetedNodes);
        this.trigger("on_all_formats_removed_handlers");
        this.dependencies.history.addStep();
    }

    removeFontSizeFormat(el) {
        this.removeFormats(["fontSize", "setFontSizeClassName"], [el, ...descendants(el)]);
    }

    /**
     * Return true if the current selection on the editable contains a formated
     * node
     *
     * @param {String} format 'bold'|'italic'|'underline'|'strikeThrough'|'switchDirection'
     * @param {Node[]} [targetedNodes]
     * @returns {boolean}
     */
    hasSelectionFormat(format, targetedNodes = this.dependencies.selection.getTargetedNodes()) {
        const targetedTextNodes = targetedNodes.filter(
            (node) =>
                node.matches?.(PROTECTED_QWEB_SELECTOR) ||
                (isTextNode(node) && (isVisibleTextNode(node) || isZWS(node)))
        );
        const isFormatted = formatsSpecs[format].isFormatted;
        return targetedTextNodes.some((n) => isFormatted(n, { editable: this.editable }));
    }
    /**
     * Return true if the current selection on the editable appears as the given
     * format. The selection is considered to appear as that format if every
     * text node in it appears as that format.
     *
     * @param {String} format 'bold'|'italic'|'underline'|'strikeThrough'|'switchDirection'
     * @param {Node[]} [targetedNodes]
     * @returns {boolean}
     */
    isSelectionFormat(format, targetedNodes = this.dependencies.selection.getTargetedNodes()) {
        const isFormatted = formatsSpecs[format].isFormatted;
        const isNonFormattedWhiteSpaces = (node) =>
            /^(\s|\n)+$/.test(node.nodeValue) && !isFormatted(node, { editable: this.editable });
        const targetedTextNodes = targetedNodes.filter(
            (node) =>
                isTextNode(node) &&
                !isNonFormattedWhiteSpaces(node) &&
                this.dependencies.selection.isNodeEditable(node)
        );
        return (
            targetedTextNodes.length &&
            targetedTextNodes.every(
                (node) =>
                    isZwnbsp(node) ||
                    isEmptyTextNode(node) ||
                    isFormatted(node, { editable: this.editable })
            )
        );
    }

    hasAnyFormat(targetedNodes) {
        const editableTargetedNodes = targetedNodes.filter(
            this.dependencies.selection.isNodeEditable
        );
        for (const format of Object.keys(formatsSpecs)) {
            if (
                formatsSpecs[format].removeStyle &&
                this.hasSelectionFormat(format, editableTargetedNodes)
            ) {
                return true;
            }
        }
        return editableTargetedNodes.some(
            (node) => this.checkPredicates("has_format_predicates", node) ?? false
        );
    }

    formatSelection(formatName, options) {
        if (this._formatSelection(formatName, options) && !options?.removeFormat) {
            this.dependencies.history.addStep();
        }
    }

    // @todo phoenix: refactor this method.
    _formatSelection(formatName, { applyStyle, formatProps } = {}) {
        const deepSelection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const anchorElement = deepSelection.anchorNode;
        const focusElement = deepSelection.focusNode;
        if (
            anchorElement === focusElement &&
            !isContentEditable(anchorElement) &&
            !closestElement(anchorElement, PROTECTED_QWEB_SELECTOR)
        ) {
            return;
        }
        this.dependencies.selection.selectAroundNonEditable();
        // note: does it work if selection is in opposite direction?
        const selection = this.dependencies.split.splitSelection();
        if (typeof applyStyle === "undefined") {
            applyStyle = !this.isSelectionFormat(formatName);
        }

        const formattedNodes = new Set();
        if (
            this.delegateTo("format_selection_overrides", formatName, formattedNodes, {
                applyStyle,
                formatProps,
            })
        ) {
            return;
        }

        let zws;
        if (selection.isCollapsed) {
            if (isTextNode(selection.anchorNode) && selection.anchorNode.textContent === "\u200b") {
                zws = selection.anchorNode;
                this.dependencies.selection.setSelection({
                    anchorNode: zws,
                    anchorOffset: 0,
                    focusNode: zws,
                    focusOffset: 1,
                });
            } else {
                zws = this.insertAndSelectZws();
            }
        }

        const systemNodesSelector = this.getResource("system_node_selectors").join(", ");
        const selectedTextNodes = /** @type { Text[] } **/ (
            this.dependencies.selection
                .getTargetedNodes()
                .filter(
                    (n) =>
                        (!systemNodesSelector || !closestElement(n, systemNodesSelector)) &&
                        this.dependencies.selection.areNodeContentsFullySelected(n) &&
                        ((isTextNode(n) && (isVisibleTextNode(n) || isZWS(n))) ||
                            (n.nodeName === "BR" &&
                                (isFakeLineBreak(n) ||
                                    previousLeaf(n, closestBlock(n))?.nodeName === "BR"))) &&
                        isContentEditable(n)
                )
        );
        const unformattedTextNodes = selectedTextNodes.filter(
            (n) =>
                !formattedNodes.has(n) &&
                (this.checkPredicates("is_formattable_node_predicates", n) ?? true)
        );
        const formatSpec = formatsSpecs[formatName];
        for (const node of unformattedTextNodes) {
            const inlineAncestors = [];
            /** @type { Node } */
            let currentNode = node;
            let parentNode = node.parentElement;

            // Remove the format on all inline ancestors until a block or an element
            // with a class that is not indicated as splittable.
            const isClassListSplittable = (classList) =>
                [...classList].every(
                    (className) =>
                        this.checkPredicates("is_format_class_predicates", className) ?? false
                );

            // Special case: if the parent node is unsplittable and fully selected,
            // we should make sure the span is applied outside of it.
            if (
                parentNode &&
                !isBlock(parentNode) &&
                this.dependencies.split.isUnsplittable(parentNode) &&
                this.dependencies.selection.areNodeContentsFullySelected(parentNode)
            ) {
                inlineAncestors.push(parentNode);
            }

            while (
                parentNode &&
                !isBlock(parentNode) &&
                (!this.dependencies.split.isUnsplittable(parentNode) ||
                    parentNode.dataset.textEffect) &&
                (parentNode.classList.length === 0 || isClassListSplittable(parentNode.classList))
            ) {
                const isUselessZws =
                    parentNode.tagName === "SPAN" &&
                    parentNode.hasAttribute("data-oe-zws-empty-inline") &&
                    parentNode.getAttributeNames().length === 1;

                if (isUselessZws) {
                    unwrapContents(parentNode);
                } else {
                    const newLastAncestorInlineFormat = this.dependencies.split.splitAroundUntil(
                        currentNode,
                        parentNode
                    );
                    removeFormat(newLastAncestorInlineFormat, formatSpec);
                    if (["setFontSizeClassName", "fontSize"].includes(formatName) && applyStyle) {
                        removeClass(newLastAncestorInlineFormat, "o_default_font_size");
                    }
                    if (newLastAncestorInlineFormat.isConnected) {
                        inlineAncestors.push(newLastAncestorInlineFormat);
                        currentNode = newLastAncestorInlineFormat;
                    }
                }

                parentNode = currentNode.parentElement;
            }

            const firstBlockOrClassHasFormat = formatSpec.isFormatted(parentNode, formatProps);
            if (firstBlockOrClassHasFormat && !applyStyle) {
                const isParentNodeBlockAndCompletelySelected =
                    isBlock(parentNode) &&
                    this.dependencies.selection.areNodeContentsFullySelected(parentNode);
                if (
                    isParentNodeBlockAndCompletelySelected &&
                    formatName === "setFontSizeClassName"
                ) {
                    for (const node of [parentNode, ...descendants(parentNode).filter(isElement)]) {
                        removeFormat(node, formatSpec);
                    }
                } else {
                    formatSpec.addNeutralStyle &&
                        formatSpec.addNeutralStyle(getOrCreateSpan(node, inlineAncestors));
                }
            } else if (
                (!firstBlockOrClassHasFormat || parentNode.nodeName === "LI") &&
                applyStyle
            ) {
                const tag = formatSpec.tagName && this.document.createElement(formatSpec.tagName);
                if (tag) {
                    node.after(tag);
                    tag.append(node);

                    if (!formatSpec.isFormatted(tag, formatProps)) {
                        tag.after(node);
                        tag.remove();
                        formatSpec.addStyle(getOrCreateSpan(node, inlineAncestors), formatProps);
                    }
                } else if (formatName !== "fontSize" || formatProps.size !== undefined) {
                    formatSpec.addStyle(getOrCreateSpan(node, inlineAncestors), formatProps);
                }
            }
        }

        if (zws) {
            const siblings = [...zws.parentElement.childNodes];
            if (
                !isBlock(zws.parentElement) &&
                unformattedTextNodes.includes(siblings[0]) &&
                unformattedTextNodes.includes(siblings[siblings.length - 1])
            ) {
                zws.parentElement.setAttribute("data-oe-zws-empty-inline", "");
            } else {
                const span = this.document.createElement("span");
                span.setAttribute("data-oe-zws-empty-inline", "");
                zws.before(span);
                span.append(zws);
            }
        }

        if (
            unformattedTextNodes.length === 1 &&
            unformattedTextNodes[0] &&
            unformattedTextNodes[0].textContent === "\u200B"
        ) {
            this.dependencies.selection.setCursorEnd(unformattedTextNodes[0]);
        } else if (selectedTextNodes.length) {
            const firstNode = selectedTextNodes[0];
            const lastNode = selectedTextNodes[selectedTextNodes.length - 1];
            let newSelection;
            if (selection.direction === DIRECTIONS.RIGHT) {
                newSelection = {
                    anchorNode: firstNode,
                    anchorOffset: 0,
                    focusNode: lastNode,
                    focusOffset: lastNode.length,
                };
            } else {
                newSelection = {
                    anchorNode: lastNode,
                    anchorOffset: lastNode.length,
                    focusNode: firstNode,
                    focusOffset: 0,
                };
            }
            this.dependencies.selection.setSelection(newSelection, { normalize: false });
            return true;
        }
        // To ensure history step is added when overrides apply formatting.
        // @see formatSelection
        return !!formattedNodes.size;
    }

    normalize(root) {
        for (const el of selectElements(root, "[data-oe-zws-empty-inline]")) {
            if (!allWhitespaceRegex.test(el.textContent)) {
                // The element has some meaningful text. Remove the ZWS in it.
                delete el.dataset.oeZwsEmptyInline;
                this.cleanZWS(el);
                if (
                    el.tagName === "SPAN" &&
                    el.getAttributeNames().length === 0 &&
                    el.classList.length === 0
                ) {
                    // Useless span, unwrap it.
                    unwrapContents(el);
                }
            }
        }
        this.mergeAdjacentInlines(root);
    }

    cleanForSave(root, { preserveSelection = false } = {}) {
        for (const element of root.querySelectorAll("[data-oe-zws-empty-inline]")) {
            let currentElement = element.parentElement;
            this.cleanElement(element, { preserveSelection });
            while (
                currentElement &&
                !isBlock(currentElement) &&
                !currentElement.childNodes.length
            ) {
                const parentElement = currentElement.parentElement;
                currentElement.remove();
                currentElement = parentElement;
            }
            if (currentElement && isBlock(currentElement)) {
                fillEmpty(currentElement);
            }
        }
        this.mergeAdjacentInlines(root, { preserveSelection });
    }

    removeEmptyInlineElement(selectionData) {
        const { anchorNode } = selectionData.editableSelection;
        const blockEl = closestBlock(anchorNode);
        if (!blockEl) {
            return;
        }
        const inlineElement = findFurthest(
            closestElement(anchorNode),
            blockEl,
            (e) => isPhrasingContent(e) && !isVisible(e) && !hasVisibleContent(e)
        );
        if (
            this.lastEmptyInlineElement?.isConnected &&
            this.lastEmptyInlineElement !== inlineElement
        ) {
            // Remove last empty inline element.
            this.cleanElement(this.lastEmptyInlineElement, { preserveSelection: true });
        }
        // Skip if current block is empty.
        if (inlineElement && !isEmptyBlock(blockEl)) {
            this.lastEmptyInlineElement = inlineElement;
        } else {
            this.lastEmptyInlineElement = null;
        }
    }

    cleanElement(element, { preserveSelection }) {
        delete element.dataset.oeZwsEmptyInline;
        if (!allWhitespaceRegex.test(element.textContent)) {
            // The element has some meaningful text. Remove the ZWS in it.
            this.cleanZWS(element, { preserveSelection });
            return;
        }
        if (this.dependencies.delete.isUnremovable(element)) {
            return;
        }
        if (
            ![...element.classList].every(
                (c) => this.checkPredicates("is_format_class_predicates", c) ?? false
            )
        ) {
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

    cleanZWS(element, { preserveSelection = true } = {}) {
        const textNodes = descendants(element).filter(isTextNode);
        const cursors = preserveSelection ? this.dependencies.selection.preserveSelection() : null;
        for (const node of textNodes) {
            cleanTextNode(node, "\u200B", cursors);
        }
        cursors?.restore();
    }

    insertText(selection, content) {
        if (selection.anchorNode.nodeType === Node.TEXT_NODE) {
            selection = this.dependencies.selection.setSelection(
                {
                    anchorNode: selection.anchorNode.parentElement,
                    anchorOffset: splitTextNode(selection.anchorNode, selection.anchorOffset),
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
        this.dependencies.selection.setSelection(
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
        const selection = this.dependencies.selection.getEditableSelection();
        const zws = this.insertText(selection, "\u200B");
        splitTextNode(zws, selection.anchorOffset);
        return zws;
    }

    onBeforeInput(ev) {
        if (
            ev.inputType.startsWith("format") &&
            !isHtmlContentSupported(this.dependencies.selection.getEditableSelection())
        ) {
            ev.preventDefault();
        }
        if (ev.inputType === "insertText") {
            const selection = this.dependencies.selection.getEditableSelection();
            if (!selection.isCollapsed) {
                return;
            }
            // Links are a special case here. When typing, link
            // element gets removed automatically whereas
            // other inline tags would be preserved.
            const element = closestElement(selection.anchorNode, ":not(a)");
            if (element.hasAttribute("data-oe-zws-empty-inline")) {
                // Select its ZWS content to make sure the text will be
                // inserted inside the element, and not before (outside) it.
                // This addresses an undesired behavior of the
                // contenteditable.
                const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesIn(element);
                this.dependencies.selection.setSelection({
                    anchorNode,
                    anchorOffset,
                    focusNode,
                    focusOffset,
                });
            }
        }
    }

    /**
     * @param {Node} root
     * @param {Object} [options]
     * @param {boolean} [options.preserveSelection=true]
     */
    mergeAdjacentInlines(root, { preserveSelection = true } = {}) {
        this.trigger("on_will_merge_adjacent_siblings_handlers", root);
        let selectionToRestore = null;
        for (const node of [root, ...descendants(root)].filter(isElement)) {
            if (this.shouldBeMergedWithPreviousSibling(node)) {
                if (preserveSelection) {
                    selectionToRestore ??= this.dependencies.selection.preserveSelection();
                    selectionToRestore.update(callbacksForCursorUpdate.merge(node));
                }
                node.previousSibling.append(...childNodes(node));
                node.remove();
            }
        }
        selectionToRestore?.restore();
        this.trigger("on_merged_adjacent_siblings_handlers", root);
    }

    shouldBeMergedWithPreviousSibling(node) {
        const isMergeable = (node) =>
            FORMATTABLE_TAGS.includes(node.nodeName) &&
            (this.checkPredicates("is_node_splittable_predicates", node) ?? true);
        const previousSibling = node.previousSibling;
        return (
            !isSelfClosingElement(node) &&
            isMergeable(node) &&
            this.areSimilarElements(node, previousSibling)
        );
    }

    areSimilarElements(node, node2) {
        if (![node, node2].every((n) => n?.nodeType === Node.ELEMENT_NODE)) {
            return false; // The nodes don't both exist or aren't both elements.
        }
        if (node.nodeName !== node2.nodeName) {
            return false; // The nodes aren't the same type of element.
        }
        for (const name of new Set([...node.getAttributeNames(), ...node2.getAttributeNames()])) {
            if (name === "style") {
                if (!hasSameStyleAttributes(node, node2)) {
                    return false;
                }
            } else if (name === "class") {
                if (!hasSameClasses(node, node2)) {
                    return false; // The nodes don't have the same classes.
                }
            } else if (node.getAttribute(name) !== node2.getAttribute(name)) {
                return false; // The nodes don't have the same attributes.
            }
        }
        if (
            [node, node2].some(
                (n) => hasPseudoElementContent(n, ":before") || hasPseudoElementContent(n, ":after")
            )
        ) {
            return false; // The nodes have pseudo elements with content.
        }
        if (isBlock(node)) {
            return false;
        }
        const nodeStyle = getComputedStyle(node);
        const node2Style = getComputedStyle(node2);
        for (const override of this.getResource("are_similar_elements_overrides")) {
            const overrideResult = override({ node, nodeStyle, node2, node2Style });
            if (overrideResult !== undefined) {
                return overrideResult;
            }
        }
        return (
            !+nodeStyle.padding.replace(NOT_A_NUMBER, "") &&
            !+node2Style.padding.replace(NOT_A_NUMBER, "") &&
            !+nodeStyle.margin.replace(NOT_A_NUMBER, "") &&
            !+node2Style.margin.replace(NOT_A_NUMBER, "")
        );
    }

    canFormatContent(selection) {
        return (
            isHtmlContentSupported(selection) &&
            this.dependencies.selection.getTargetedNodes().every((node) => isStylable(node))
        );
    }
}

function getOrCreateSpan(node, ancestors) {
    const document = node.ownerDocument;
    const span = ancestors.find(
        (element) =>
            element.tagName === "SPAN" && element.isConnected && !element.dataset.textEffect
    );
    const lastInlineAncestor = ancestors.findLast(
        (element) => !isBlock(element) && element.isConnected
    );
    if (span) {
        return span;
    } else {
        const span = document.createElement("span");
        // Apply font span above current inline top ancestor so that
        // the font style applies to the other style tags as well.
        if (lastInlineAncestor) {
            lastInlineAncestor.after(span);
            span.append(lastInlineAncestor);
        } else {
            node.after(span);
            span.append(node);
        }
        return span;
    }
}
function removeFormat(node, formatSpec) {
    const document = node.ownerDocument;
    node = closestElement(node);
    if (formatSpec.hasStyle(node)) {
        formatSpec.removeStyle(node);
        if (["SPAN", "FONT"].includes(node.tagName) && !node.getAttributeNames().length) {
            return unwrapContents(node);
        }
    }

    if (formatSpec.isTag && formatSpec.isTag(node)) {
        const attributesNames = node
            .getAttributeNames()
            .filter((name) => name !== "data-oe-zws-empty-inline");
        if (attributesNames.length) {
            // Change tag name
            const newNode = document.createElement("span");
            while (node.firstChild) {
                newNode.appendChild(node.firstChild);
            }
            for (let index = node.attributes.length - 1; index >= 0; --index) {
                newNode.attributes.setNamedItem(node.attributes[index].cloneNode());
            }
            node.parentNode.replaceChild(newNode, node);
        } else {
            unwrapContents(node);
        }
    }
}
