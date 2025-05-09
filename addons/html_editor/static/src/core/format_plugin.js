import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import { cleanTextNode, splitTextNode, unwrapContents, fillEmpty } from "../utils/dom";
import {
    areSimilarElements,
    isContentEditable,
    isEmptyTextNode,
    isEmptyBlock,
    isSelfClosingElement,
    isTextNode,
    isVisibleTextNode,
    isZwnbsp,
    isZWS,
    previousLeaf,
} from "../utils/dom_info";
import {
    childNodes,
    closestElement,
    descendants,
    selectElements,
    findFurthest,
} from "../utils/dom_traversal";
import { FONT_SIZE_CLASSES, formatsSpecs } from "../utils/formatting";
import { boundariesIn, boundariesOut, DIRECTIONS, leftPos, rightPos } from "../utils/position";
import { prepareUpdate } from "@html_editor/utils/dom_state";
import { _t } from "@web/core/l10n/translation";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { withSequence } from "@html_editor/utils/resource";
import { isFakeLineBreak } from "../utils/dom_state";

const allWhitespaceRegex = /^[\s\u200b]*$/;

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

export class FormatPlugin extends Plugin {
    static id = "format";
    static dependencies = ["selection", "history", "input", "split"];
    // TODO ABD: refactor to handle Knowledge comments inside this plugin without sharing mergeAdjacentInlines.
    static shared = [
        "isSelectionFormat",
        "insertAndSelectZws",
        "mergeAdjacentInlines",
        "formatSelection",
    ];
    resources = {
        user_commands: [
            {
                id: "formatBold",
                description: _t("Toggle bold"),
                icon: "fa-bold",
                run: this.formatSelection.bind(this, "bold"),
            },
            {
                id: "formatItalic",
                description: _t("Toggle italic"),
                icon: "fa-italic",
                run: this.formatSelection.bind(this, "italic"),
            },
            {
                id: "formatUnderline",
                description: _t("Toggle underline"),
                icon: "fa-underline",
                run: this.formatSelection.bind(this, "underline"),
            },
            {
                id: "formatStrikethrough",
                description: _t("Toggle strikethrough"),
                icon: "fa-strikethrough",
                run: this.formatSelection.bind(this, "strikeThrough"),
            },
            {
                id: "formatFontSize",
                run: ({ size }) =>
                    this.formatSelection("fontSize", {
                        applyStyle: true,
                        formatProps: { size },
                    }),
            },
            {
                id: "formatFontSizeClassName",
                run: ({ className }) =>
                    this.formatSelection("setFontSizeClassName", {
                        applyStyle: true,
                        formatProps: { className },
                    }),
            },
            {
                id: "removeFormat",
                description: (sel, nodes) =>
                    nodes && this.hasAnyFormat(nodes)
                        ? _t("Remove Format")
                        : _t("Selection has no format"),
                icon: "fa-eraser",
                run: this.removeFormat.bind(this),
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
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatBold",
                isActive: isFormatted(this, "bold"),
            },
            {
                id: "italic",
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatItalic",
                isActive: isFormatted(this, "italic"),
            },
            {
                id: "underline",
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatUnderline",
                isActive: isFormatted(this, "underline"),
            },
            {
                id: "strikethrough",
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                commandId: "formatStrikethrough",
                isActive: isFormatted(this, "strikeThrough"),
            },
            withSequence(20, {
                id: "remove_format",
                groupId: "decoration",
                commandId: "removeFormat",
                isDisabled: (sel, nodes) => !this.hasAnyFormat(nodes),
            }),
        ],
        /** Handlers */
        beforeinput_handlers: withSequence(20, this.onBeforeInput.bind(this)),
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.normalize.bind(this),
        selectionchange_handlers: this.removeEmptyInlineElement.bind(this),

        intangible_char_for_keyboard_navigation_predicates: (_, char) => char === "\u200b",
    };

    removeFormat() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        this.dispatchTo("remove_format_handlers");
        for (const format of Object.keys(formatsSpecs)) {
            if (
                !formatsSpecs[format].removeStyle ||
                !this.hasSelectionFormat(format, targetedNodes)
            ) {
                continue;
            }
            this._formatSelection(format, { applyStyle: false });
        }
        this.dependencies.history.addStep();
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
        const targetedTextNodes = targetedNodes.filter(isTextNode);
        const isFormatted = formatsSpecs[format].isFormatted;
        return targetedTextNodes.some((n) => isFormatted(n, this.editable));
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
        const targetedTextNodes = targetedNodes.filter(
            (node) =>
                isTextNode(node) &&
                !isZwnbsp(node) &&
                !isEmptyTextNode(node) &&
                (!/^\n+$/.test(node.nodeValue) || !isBlock(closestElement(node)))
        );
        const isFormatted = formatsSpecs[format].isFormatted;
        return (
            targetedTextNodes.length && targetedTextNodes.every((node) => isFormatted(node, this.editable))
        );
    }

    hasAnyFormat(targetedNodes) {
        for (const format of Object.keys(formatsSpecs)) {
            if (
                formatsSpecs[format].removeStyle &&
                this.hasSelectionFormat(format, targetedNodes)
            ) {
                return true;
            }
        }
        return targetedNodes.some((node) =>
            this.getResource("has_format_predicates").some((predicate) => predicate(node))
        );
    }

    formatSelection(...args) {
        this.delegateTo("format_selection_overrides", ...args);
        if (this._formatSelection(...args)) {
            this.dependencies.history.addStep();
        }
    }

    // @todo phoenix: refactor this method.
    _formatSelection(formatName, { applyStyle, formatProps } = {}) {
        this.dependencies.selection.selectAroundNonEditable();
        // note: does it work if selection is in opposite direction?
        const selection = this.dependencies.split.splitSelection();
        if (typeof applyStyle === "undefined") {
            applyStyle = !this.isSelectionFormat(formatName);
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

        const selectedTextNodes = /** @type { Text[] } **/ (
            this.dependencies.selection
                .getTargetedNodes()
                .filter(
                    (n) =>
                        this.dependencies.selection.areNodeContentsFullySelected(n) &&
                        ((isTextNode(n) &&
                            (isVisibleTextNode(n) ||
                                isZWS(n) ||
                                (/^\n+$/.test(n.nodeValue) && !applyStyle))) ||
                            (n.nodeName === "BR" &&
                                (isFakeLineBreak(n) ||
                                    previousLeaf(n, closestBlock(n))?.nodeName === "BR"))) &&
                        isContentEditable(n)
                )
        );
        const unformattedTextNodes = selectedTextNodes.filter((n) => {
            const listItem = closestElement(n, "li");
            if (listItem && this.dependencies.selection.isNodeContentsFullySelected(listItem)) {
                const hasFontSizeStyle =
                    formatName === "setFontSizeClassName"
                        ? listItem.classList.contains(formatProps?.className)
                        : listItem.style.fontSize;
                return !hasFontSizeStyle;
            }
            return true;
        });

        const tagetedFieldNodes = new Set(
            this.dependencies.selection
                .getTargetedNodes()
                .map((n) => closestElement(n, "*[t-field],*[t-out],*[t-esc]"))
                .filter(Boolean)
        );
        const formatSpec = formatsSpecs[formatName];
        for (const node of unformattedTextNodes) {
            const inlineAncestors = [];
            /** @type { Node } */
            let currentNode = node;
            let parentNode = node.parentElement;

            // Remove the format on all inline ancestors until a block or an element
            // with a class that is not related to font size (in case the formatting
            // comes from the class).

            while (
                parentNode &&
                !isBlock(parentNode) &&
                !this.dependencies.split.isUnsplittable(parentNode) &&
                (parentNode.classList.length === 0 ||
                    [...parentNode.classList].every((cls) => FONT_SIZE_CLASSES.includes(cls)))
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
                    if (newLastAncestorInlineFormat.isConnected) {
                        inlineAncestors.push(newLastAncestorInlineFormat);
                        currentNode = newLastAncestorInlineFormat;
                    }
                }

                parentNode = currentNode.parentElement;
            }

            const firstBlockOrClassHasFormat = formatSpec.isFormatted(parentNode, formatProps);
            if (firstBlockOrClassHasFormat && !applyStyle) {
                formatSpec.addNeutralStyle &&
                    formatSpec.addNeutralStyle(getOrCreateSpan(node, inlineAncestors));
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

        for (const targetedFieldNode of tagetedFieldNodes) {
            if (applyStyle) {
                formatSpec.addStyle(targetedFieldNode, formatProps);
            } else {
                formatSpec.removeStyle(targetedFieldNode);
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
            this.dependencies.selection.setCursorStart(unformattedTextNodes[0]);
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
        if (tagetedFieldNodes.size > 0) {
            return true;
        }
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

    cleanForSave({ root, preserveSelection = false } = {}) {
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
        const inlineElement = findFurthest(
            closestElement(anchorNode),
            blockEl,
            (e) => !isBlock(e) && e.textContent === "\u200b"
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
        if (this.getResource("unremovable_node_predicates").some((p) => p(element))) {
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
        if (ev.inputType === "insertText") {
            const selection = this.dependencies.selection.getEditableSelection();
            if (!selection.isCollapsed) {
                return;
            }
            const element = closestElement(selection.anchorNode);
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
        let selectionToRestore = null;
        for (const node of descendants(root)) {
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
    }

    shouldBeMergedWithPreviousSibling(node) {
        const isMergeable = (node) =>
            !this.getResource("unsplittable_node_predicates").some((predicate) => predicate(node));
        return (
            !isSelfClosingElement(node) &&
            areSimilarElements(node, node.previousSibling) &&
            isMergeable(node)
        );
    }
}

function getOrCreateSpan(node, ancestors) {
    const document = node.ownerDocument;
    const span = ancestors.find((element) => element.tagName === "SPAN" && element.isConnected);
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
