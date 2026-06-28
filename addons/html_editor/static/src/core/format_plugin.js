import { prepareUpdate } from "@html_editor/utils/dom_state";
import { withSequence } from "@html_editor/utils/resource";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import { cleanTextNode, fillEmpty, splitTextNode, unwrapContents } from "../utils/dom";
import {
    hasPseudoElementContent,
    hasSameClasses,
    hasSameStyleAttributes,
    isBold,
    isContentEditable,
    isElement,
    isEmpty,
    isEmptyBlock,
    isItalic,
    isPhrasingContent,
    isSelfClosingElement,
    isStrikeThrough,
    isTextNode,
    isUnderline,
    isVisibleTextNode,
    isZWS,
    paragraphRelatedElementsSelector,
    previousLeaf,
} from "../utils/dom_info";
import {
    childNodes,
    closestElement,
    descendants,
    findUpTo,
    selectElements,
} from "../utils/dom_traversal";
import { FORMATTABLE_TAGS, removeStyle } from "../utils/formatting";
import { boundariesIn, leftPos, rightPos } from "../utils/position";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

const allWhitespaceRegex = /^[\s\u200b]*$/;
const NOT_A_NUMBER = /[^\d]/g;

/**
 * @typedef {Object} FormatShared
 * @property { FormatPlugin['canFormatContent'] } canFormatContent
 * @property { FormatPlugin['getOrCreateZws'] } getOrCreateZws
 * @property { FormatPlugin['mergeAdjacentInlines'] } mergeAdjacentInlines
 * @property { FormatPlugin['removeSelectionFormats'] } removeSelectionFormats
 * @property { FormatPlugin['requestFormat'] } requestFormat
 */

/**
 * @typedef {Object} FormatSpec
 * @property {string} id
 * @property {string} [tagName]
 * @property {(node: Node, formatProps?: object) => boolean} isFormatted
 * @property {(node: Node) => boolean} [isTag]
 * @property {(node: Node) => boolean} hasStyle
 * @property {(node: Node, formatProps?: object) => void} addStyle
 * @property {(node: Node) => void} [addNeutralStyle]
 * @property {(node: Node) => void} removeStyle
 */

/**
 * @typedef {FormatSpec[]} format_specs
 * @typedef {(() => void)[]} before_format_handlers
 * @typedef {(() => void)[]} on_all_formats_removed_handlers
 * @typedef {(() => void)[]} on_format_requested_handlers
 * @typedef {(() => void)[]} on_collapsed_formats_removed_handlers
 * @typedef {((node: Node, formatName: string, applyStyle: boolean) => void)[]} on_format_applied_handlers
 * @typedef {((root: Node) => void)[]} on_will_merge_adjacent_siblings_handlers
 * @typedef {((root: Node) => void)[]} on_merged_adjacent_siblings_handlers
 *
 * @typedef {((node: Node, formatName: string, options: { applyStyle: boolean, formatProps: object }) => Node | undefined)[]} formattable_node_providers
 * @typedef {((selection: EditorSelection) => boolean | undefined)[]} can_format_content_predicates
 * @typedef {((className: string) => boolean | undefined)[]} is_format_class_predicates
 * @typedef {((node: Node) => boolean | undefined)[]} is_formattable_node_predicates
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
        "canFormatContent",
        "getOrCreateZws",
        "mergeAdjacentInlines",
        "removeSelectionFormats",
        "requestFormat",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "formatBold",
                description: _t("Toggle bold"),
                icon: "fa-bold",
                run: this.requestFormat.bind(this, "bold"),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "formatItalic",
                description: _t("Toggle italic"),
                icon: "fa-italic",
                run: this.requestFormat.bind(this, "italic"),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "formatUnderline",
                description: _t("Toggle underline"),
                icon: "fa-underline",
                run: this.requestFormat.bind(this, "underline"),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "formatStrikethrough",
                description: _t("Toggle strikethrough"),
                icon: "fa-strikethrough",
                run: this.requestFormat.bind(this, "strikeThrough"),
                isAvailable: this.canFormatContent.bind(this),
            },
            {
                id: "removeFormat",
                description: (sel, nodes) =>
                    nodes && this.hasAnyFormat(nodes)
                        ? _t("Remove Format (Ctrl + Space)")
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
                isActive: () =>
                    this.activeFormats["bold"]?.applyStyle ?? this.isFormatActive("bold"),
            },
            {
                id: "italic",
                description: _t("Italic (Ctrl + I)"),
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatItalic",
                isActive: () =>
                    this.activeFormats["italic"]?.applyStyle ?? this.isFormatActive("italic"),
            },
            {
                id: "underline",
                description: _t("Underline (Ctrl + U)"),
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatUnderline",
                isActive: () =>
                    this.activeFormats["underline"]?.applyStyle ?? this.isFormatActive("underline"),
            },
            {
                id: "strikethrough",
                description: _t("Strikethrough (Ctrl + 5)"),
                groupId: "decoration",
                commandId: "formatStrikethrough",
                isActive: () =>
                    this.activeFormats["strikeThrough"]?.applyStyle ??
                    this.isFormatActive("strikeThrough"),
            },
            withSequence(20, {
                id: "remove_format",
                groupId: "decoration",
                commandId: "removeFormat",
                isDisabled: (sel, nodes) => !this.hasAnyFormat(nodes),
            }),
        ],
        format_specs: [
            {
                id: "italic",
                tagName: "em",
                isFormatted: isItalic,
                isTag: (node) => ["EM", "I"].includes(node.tagName),
                hasStyle: (node) => Boolean(node.style && node.style["font-style"]),
                addStyle: (node) => (node.style["font-style"] = "italic"),
                addNeutralStyle: (node) => (node.style["font-style"] = "normal"),
                removeStyle: (node) => removeStyle(node, "font-style"),
            },
            {
                id: "bold",
                tagName: "strong",
                isFormatted: isBold,
                isTag: (node) => ["STRONG", "B"].includes(node.tagName),
                hasStyle: (node) => Boolean(node.style && node.style["font-weight"]),
                addStyle: (node) => (node.style["font-weight"] = "bolder"),
                addNeutralStyle: (node) => {
                    node.style["font-weight"] = "normal";
                },
                removeStyle: (node) => removeStyle(node, "font-weight"),
            },
            {
                id: "underline",
                tagName: "u",
                isFormatted: isUnderline,
                isTag: (node) => node.tagName === "U",
                hasStyle: (node) =>
                    node.style &&
                    (node.style["text-decoration"].includes("underline") ||
                        node.style["text-decoration-line"].includes("underline")),
                addStyle: (node) => (node.style["text-decoration-line"] += " underline"),
                removeStyle: (node) =>
                    removeStyle(
                        node,
                        node.style["text-decoration"].includes("underline")
                            ? "text-decoration"
                            : "text-decoration-line",
                        "underline"
                    ),
            },
            {
                id: "strikeThrough",
                tagName: "s",
                isFormatted: isStrikeThrough,
                isTag: (node) => node.tagName === "S",
                hasStyle: (node) =>
                    node.style &&
                    (node.style["text-decoration"].includes("line-through") ||
                        node.style["text-decoration-line"].includes("line-through")),
                addStyle: (node) => (node.style["text-decoration-line"] += " line-through"),
                removeStyle: (node) =>
                    removeStyle(
                        node,
                        node.style["text-decoration"].includes("line-through")
                            ? "text-decoration"
                            : "text-decoration-line",
                        "line-through"
                    ),
            },
        ],
        /** Handlers */
        on_beforeinput_handlers: withSequence(20, this.onBeforeInput.bind(this)),
        on_selectionchange_handlers: this.clearPendingFormats.bind(this),
        before_insert_handlers: this.beforeInsert.bind(this),
        on_deleted_handlers: this.convertEmptyFormatToPendingIntent.bind(this),

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

    setup() {
        this.activeFormats = {};
        this.formatSpecs = this.getResource("format_specs");
    }

    getFormatSpec(formatName) {
        return this.formatSpecs.find((spec) => spec.id === formatName);
    }

    /**
     * Remove formats from the current selection, toggling each off via
     * requestFormat.
     *
     * @param {string[]} [formatNames] formats to remove (defaults to all)
     */
    removeSelectionFormats(formatNames = this.formatSpecs.map((spec) => spec.id)) {
        for (const formatName of formatNames) {
            if (this.getFormatSpec(formatName).removeStyle && this.hasFormat(formatName)) {
                this.requestFormat(formatName, { applyStyle: false, commit: false });
            }
        }
    }

    /**
     * When a delete leaves the cursor inside an empty styled inline, convert
     * that inline back into a pending format intent ({@link activeFormats}) so
     * the format survives for the next typed character.
     */
    convertEmptyFormatToPendingIntent() {
        const selection = this.dependencies.selection.getEditableSelection();
        const anchorNode = selection.anchorNode;
        let element = closestElement(anchorNode);
        if (!isZWS(element) || !isPhrasingContent(element)) {
            return;
        }
        const cursor = this.dependencies.selection.preserveSelection();
        while (
            (isZWS(element) || isEmpty(element)) &&
            isPhrasingContent(element) &&
            !this.dependencies.delete.isUnremovable(element)
        ) {
            const spec = this.formatSpecs.find(
                (spec) => spec.isTag?.(element) || spec.hasStyle?.(element)
            );
            if (!spec) {
                break;
            }
            const parent = element.parentElement;
            const restore = prepareUpdate(...leftPos(anchorNode), ...rightPos(anchorNode));
            removeFormat(element, spec, cursor);
            this.activeFormats[spec.id] = { applyStyle: true };
            if (
                element.isConnected &&
                element.getAttributeNames().length === 1 &&
                element.hasAttribute("data-oe-zws-empty-inline")
            ) {
                cursor.update(callbacksForCursorUpdate.remove(element));
                element.remove();
            }
            restore();
            element = parent;
            // Delete is a special case: it triggers a selectionchange, which
            // would normally discard pending format intents (see
            // clearPendingFormats). Here we have just recorded one from the
            // emptied inline, so we skip that next clear to preserve it.
            this.skipNextFormatClear = true;
        }
        cursor.restore();
    }

    /**
     * Remove every removable format from the selection.
     *
     * For a non-collapsed selection the formats are stripped from the DOM
     * immediately. For a collapsed selection it discards any pending format
     * intents and records a pending removal for each active format, applied to
     * the next typed character (see {@link applyPendingFormats}).
     */
    removeAllFormats() {
        const sel = this.dependencies.selection.getEditableSelection();
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        if (sel.isCollapsed) {
            this.activeFormats = {}; // discard pending "apply" intents
            for (const spec of this.formatSpecs) {
                if (spec.removeStyle && this.hasFormat(spec.id, targetedNodes)) {
                    this.activeFormats[spec.id] = { applyStyle: false };
                }
            }
            this.trigger("on_collapsed_formats_removed_handlers");
            return;
        }
        this.removeSelectionFormats();
        this.trigger("on_all_formats_removed_handlers");
        this.dependencies.history.commit();
    }

    /**
     * Filters a set of nodes down to those that can carry inline formatting.
     *
     * @param {Node[]} [targetedNodes]
     * @returns {Node[]} Subset of targetedNodes that are formattable.
     */
    getFormattableNodes(targetedNodes = this.dependencies.selection.getTargetedNodes()) {
        const systemNodesSelector = this.getResource("system_node_selectors").join(", ");
        return targetedNodes.filter((node) => {
            const predicatesResult = this.checkPredicates("is_formattable_node_predicates", node);
            if (predicatesResult !== undefined) {
                return predicatesResult;
            }
            if (systemNodesSelector && closestElement(node, systemNodesSelector)) {
                return false;
            }
            if (!this.dependencies.selection.isNodeEditable(node)) {
                return false;
            }
            if (isTextNode(node)) {
                return isVisibleTextNode(node) || isZWS(node);
            }
            if (node.nodeName === "BR") {
                const prevLeaf = previousLeaf(node, closestBlock(node));
                return !prevLeaf || prevLeaf.nodeName === "BR";
            }
            return false;
        });
    }

    /**
     * Return true if the current selection on the editable contains a formatted
     * node
     *
     * @param {String} format 'bold'|'italic'|'underline'|'strikeThrough'|'switchDirection'
     * @param {Node[]} [targetedNodes]
     * @returns {boolean}
     */
    hasFormat(format, targetedNodes = this.dependencies.selection.getTargetedNodes()) {
        const nodes = this.getFormattableNodes(targetedNodes);
        const isFormatted = this.getFormatSpec(format).isFormatted;
        return nodes.some((n) => isFormatted(n, { editable: this.editable }));
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
    isFormatActive(format, targetedNodes = this.dependencies.selection.getTargetedNodes()) {
        const isFormatted = this.getFormatSpec(format).isFormatted;
        let hasFormatted = false;
        for (const node of this.getFormattableNodes(targetedNodes)) {
            if (isFormatted(node, { editable: this.editable })) {
                hasFormatted = true;
            } else if (!/^\s+$/.test(node.nodeValue)) {
                // If the node is not formatted and contains some non-whitespace
                // character, the format can't be active.
                return false;
            }
            // unformatted whitespace, skip.
        }
        return hasFormatted;
    }

    hasAnyFormat(targetedNodes) {
        const editableTargetedNodes = targetedNodes.filter(
            this.dependencies.selection.isNodeEditable
        );
        for (const spec of this.formatSpecs) {
            if (spec.removeStyle && this.hasFormat(spec.id, editableTargetedNodes)) {
                return true;
            }
        }
        return editableTargetedNodes.some(
            (node) => this.checkPredicates("has_format_predicates", node) ?? false
        );
    }

    /**
     * Toggle or set a format on the current selection.
     *
     * For a non-collapsed selection, the format is applied immediately to the
     * DOM via {@link formatSelection}.
     *
     * For a collapsed selection, nothing is mutated: the intent is recorded in
     * {@link activeFormats} and applied lazily the next time the user types
     * or a programmatic insert happens (see {@link applyPendingFormats}).
     *
     * @param {string} formatName
     * @param {Object} [options]
     * @param {boolean} [options.applyStyle]
     * @param {Object} [options.formatProps]
     */
    requestFormat(formatName, options) {
        const sel = this.dependencies.selection.getEditableSelection();
        if (!sel.isCollapsed) {
            this.formatSelection(formatName, options);
            return;
        }
        const domActive = this.isFormatActive(formatName);
        const pending = this.activeFormats[formatName];
        if (options?.applyStyle === undefined && pending?.applyStyle === !domActive) {
            delete this.activeFormats[formatName];
        } else {
            this.activeFormats[formatName] = {
                applyStyle: options?.applyStyle ?? !(pending?.applyStyle ?? domActive),
                formatProps: options?.formatProps,
            };
        }
        this.trigger("on_format_requested_handlers");
    }

    formatSelection(formatName, { applyStyle, formatProps, commit = true } = {}) {
        this.dependencies.selection.selectAroundNonEditable();
        const selection = this.dependencies.split.splitSelection();
        if (typeof applyStyle === "undefined") {
            applyStyle = !this.isFormatActive(formatName);
        }
        this.trigger("before_format_handlers");
        const cursor = this.dependencies.selection.preserveSelection();
        let targetedNodes = this.dependencies.selection.getTargetedNodes();
        if (!selection.isCollapsed && isEmptyBlock(selection.endContainer)) {
            targetedNodes = [
                ...targetedNodes,
                selection.endContainer,
                ...descendants(selection.endContainer),
            ];
        }

        const formatSpec = this.getFormatSpec(formatName);
        const unformattedNodes = [
            ...new Set(
                this.getFormattableNodes(targetedNodes).flatMap((node) => {
                    let target;
                    for (const provider of this.getResource("formattable_node_providers")) {
                        target = provider(node, formatName, { applyStyle, formatProps });
                        if (target) {
                            break;
                        }
                    }
                    if (
                        target &&
                        (this.checkPredicates("is_formattable_node_predicates", target) ?? true) &&
                        // Format can only be applied to block if it can
                        // be neutralized.
                        (!isBlock(target) || formatSpec.addNeutralStyle)
                    ) {
                        return [target];
                    }
                    const block = closestElement(node, paragraphRelatedElementsSelector);
                    if (
                        block &&
                        // we only allow to remove style from
                        // paragraphRelatedElements not apply.
                        !applyStyle &&
                        isContentEditable(block) &&
                        (this.dependencies.selection.areNodeContentsFullySelected(block) ||
                            (selection.isCollapsed && isEmptyBlock(block)))
                    ) {
                        return [block];
                    }
                    return [node];
                })
            ),
        ];

        for (const node of unformattedNodes) {
            if (isTextNode(node) || node.nodeName === "BR") {
                const { inlineAncestor, parentNode } = this.splitInlineAncestors(node, {
                    formatName,
                    cursor,
                });
                const firstBlockOrClassHasFormat = formatSpec.isFormatted(parentNode, formatProps);
                if (firstBlockOrClassHasFormat && !applyStyle) {
                    formatSpec.addNeutralStyle &&
                        formatSpec.addNeutralStyle(getOrCreateSpan(node, inlineAncestor, cursor));
                } else if (!firstBlockOrClassHasFormat && applyStyle) {
                    const tag =
                        formatSpec.tagName && this.document.createElement(formatSpec.tagName);
                    if (tag) {
                        cursor.update(callbacksForCursorUpdate.after(node, tag));
                        node.after(tag);
                        cursor.update(callbacksForCursorUpdate.append(tag, node));
                        tag.append(node);

                        if (!formatSpec.isFormatted(tag, formatProps)) {
                            cursor.update(callbacksForCursorUpdate.unwrap(tag));
                            unwrapContents(tag);
                            formatSpec.addStyle(
                                getOrCreateSpan(node, inlineAncestor, cursor),
                                formatProps
                            );
                        }
                    } else {
                        formatSpec.addStyle(
                            getOrCreateSpan(node, inlineAncestor, cursor),
                            formatProps
                        );
                    }
                }
            } else {
                const nodesToUnformat = descendants(node).filter((n) => {
                    if (!isElement(n)) {
                        return false;
                    }
                    const block =
                        closestElement(n, "LI") ??
                        closestElement(n, paragraphRelatedElementsSelector);
                    return block === node;
                });
                for (const n of [node, ...nodesToUnformat]) {
                    removeFormat(n, formatSpec, cursor);
                }
                if (applyStyle && !formatSpec.isFormatted(node, formatProps)) {
                    formatSpec.addStyle(node, formatProps);
                } else if (
                    !applyStyle &&
                    formatSpec.isFormatted(node, formatProps) &&
                    formatSpec.addNeutralStyle
                ) {
                    formatSpec.addNeutralStyle(node);
                }
            }
            this.trigger("on_format_applied_handlers", node, formatName, applyStyle);
        }

        cursor.restore();
        if (
            unformattedNodes.length === 1 &&
            unformattedNodes[0] &&
            isTextNode(unformattedNodes[0]) &&
            unformattedNodes[0].textContent === "\u200B"
        ) {
            const [anchorNode, anchorOffset, focusNode, focusOffset] = [
                ...leftPos(unformattedNodes[0]),
                ...rightPos(unformattedNodes[0]),
            ];
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset,
                focusNode,
                focusOffset,
            });
        }
        if (commit) {
            this.dependencies.history.commit();
        }
    }

    splitInlineAncestors(node, { formatName, cursor }) {
        let inlineAncestor;
        /** @type { Node } */
        let currentNode = node;
        let parentNode = node.parentElement;
        const formatSpec = this.getFormatSpec(formatName);

        // Remove the format on all inline ancestors until a block or an element
        // with a class that is not indicated as splittable.
        const isClassListSplittable = (classList) =>
            [...classList].every(
                (className) =>
                    this.checkPredicates("is_format_class_predicates", className) ?? false
            );

        while (parentNode && !isBlock(parentNode)) {
            const splittable =
                (!this.dependencies.split.isUnsplittable(parentNode) ||
                    parentNode.dataset.textEffect) &&
                (parentNode.classList.length === 0 || isClassListSplittable(parentNode.classList));

            if (splittable) {
                const newLastAncestorInlineFormat = this.dependencies.split.splitAroundUntil(
                    currentNode,
                    parentNode
                );
                removeFormat(newLastAncestorInlineFormat, formatSpec, cursor);
                if (newLastAncestorInlineFormat.isConnected) {
                    inlineAncestor = newLastAncestorInlineFormat;
                    currentNode = newLastAncestorInlineFormat;
                }
                parentNode = currentNode.parentElement;
            } else if (
                this.dependencies.split.isUnsplittable(parentNode) &&
                this.dependencies.selection.areNodeContentsFullySelected(parentNode)
            ) {
                // Special case: if the parent node is unsplittable and
                // fully selected, we should make sure the span is applied
                // outside of it.
                inlineAncestor = parentNode;
                break;
            } else {
                break;
            }
        }
        return { inlineAncestor, parentNode };
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
        return root;
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
        return root;
    }

    cleanElement(element, { preserveSelection }) {
        if (!allWhitespaceRegex.test(element.textContent)) {
            // The element has some meaningful text. Remove the ZWS in it.
            delete element.dataset.oeZwsEmptyInline;
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
        delete element.dataset.oeZwsEmptyInline;
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
        const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesIn(txt);
        this.dependencies.selection.setSelection(
            { anchorNode, anchorOffset, focusNode, focusOffset },
            { normalize: false }
        );
        return txt;
    }

    /**
     * Use the actual selection (assumed to be collapsed) and insert a
     * zero-width space at its anchor point. Then, select that zero-width
     * space. If a zero-width space already exists at the anchor point,
     * it's returned instead.
     *
     * @returns {Node} the inserted zero-width space
     */
    getOrCreateZws() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (
            selection.anchorNode.nodeType === Node.TEXT_NODE &&
            selection.anchorNode.textContent === "\u200b"
        ) {
            return selection.anchorNode;
        }
        const zws = this.insertText(selection, "\u200B");
        splitTextNode(zws, selection.anchorOffset);
        return zws;
    }

    /**
     * Discard pending format intents when the selection changes.
     */
    clearPendingFormats() {
        if (this.skipNextFormatClear) {
            this.skipNextFormatClear = false;
            return;
        }
        this.activeFormats = {};
    }

    /**
     * Apply the pending format intents recorded in {@link activeFormats} onto
     * a ZWS at the cursor.
     */
    applyPendingFormats() {
        if (!Object.keys(this.activeFormats).length) {
            return;
        }
        this.getOrCreateZws();
        for (const [formatName, { applyStyle, formatProps }] of Object.entries(
            this.activeFormats
        )) {
            this.formatSelection(formatName, { applyStyle, formatProps, commit: false });
        }
        this.activeFormats = {};
    }

    beforeInsert() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (!selection.isCollapsed) {
            return;
        }
        this.applyPendingFormats();
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
            this.applyPendingFormats();
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
        const predicatesResult = this.checkPredicates("can_format_content_predicates", selection);
        if (predicatesResult !== undefined) {
            return predicatesResult && isHtmlContentSupported(selection);
        }
        const { anchorNode, focusNode } = selection;
        if (anchorNode === focusNode && !isContentEditable(anchorNode)) {
            return false;
        }
        return isHtmlContentSupported(selection);
    }
}

function getOrCreateSpan(node, ancestor, cursor) {
    const document = node.ownerDocument;
    if (ancestor) {
        const reusableSpan = findUpTo(
            node,
            ancestor.parentElement,
            (el) => el.tagName === "SPAN" && !el.dataset.textEffect
        );
        if (reusableSpan) {
            return reusableSpan;
        }
    }
    const span = document.createElement("span");
    const wrapTarget = ancestor ?? node;
    cursor.update(callbacksForCursorUpdate.after(wrapTarget, span));
    wrapTarget.after(span);
    cursor.update(callbacksForCursorUpdate.append(span, wrapTarget));
    span.append(wrapTarget);
    return span;
}
export function removeFormat(node, formatSpec, cursor) {
    const document = node.ownerDocument;
    node = closestElement(node);
    if (formatSpec.hasStyle(node)) {
        formatSpec.removeStyle(node);
        if (["SPAN", "FONT"].includes(node.tagName) && !node.getAttributeNames().length) {
            cursor?.update(callbacksForCursorUpdate.unwrap(node));
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
                cursor?.update(callbacksForCursorUpdate.append(newNode, node.firstChild));
                newNode.appendChild(node.firstChild);
            }
            for (let index = node.attributes.length - 1; index >= 0; --index) {
                newNode.attributes.setNamedItem(node.attributes[index].cloneNode());
            }
            cursor?.remapNode(node, newNode);
            node.parentNode.replaceChild(newNode, node);
        } else if (
            node.getAttributeNames().length === 1 &&
            node.hasAttribute("data-oe-zws-empty-inline")
        ) {
            cursor?.update(callbacksForCursorUpdate.remove(node));
            node.remove();
        } else {
            cursor?.update(callbacksForCursorUpdate.unwrap(node));
            unwrapContents(node);
        }
    }
}
