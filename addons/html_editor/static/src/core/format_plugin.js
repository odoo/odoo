import { Plugin } from "../plugin";
import { isBlock } from "../utils/blocks";
import { hasAnyNodesColor } from "@html_editor/utils/color";
import { cleanTextNode, unwrapContents } from "../utils/dom";
import {
    areSimilarElements,
    isContentEditable,
    isSelfClosingElement,
    isTextNode,
    isVisibleTextNode,
    isZWS,
} from "../utils/dom_info";
import { childNodes, closestElement, descendants, selectElements } from "../utils/dom_traversal";
import { FONT_SIZE_CLASSES, formatsSpecs } from "../utils/formatting";
import { boundariesIn, boundariesOut, DIRECTIONS, leftPos, rightPos } from "../utils/position";
import { prepareUpdate } from "@html_editor/utils/dom_state";
import { _t } from "@web/core/l10n/translation";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { withSequence } from "@html_editor/utils/resource";

const allWhitespaceRegex = /^[\s\u200b]*$/;

function isFormatted(formatPlugin, format) {
    return (sel, nodes) => formatPlugin.isSelectionFormat(format, nodes);
}
function hasFormat(formatPlugin) {
    return () => {
        const traversedNodes = formatPlugin.shared.getTraversedNodes();
        for (const format of Object.keys(formatsSpecs)) {
            if (
                formatsSpecs[format].removeStyle &&
                formatPlugin.isSelectionFormat(format, traversedNodes)
            ) {
                return true;
            }
        }
        const nodes = formatPlugin.shared.getTraversedNodes();
        return hasAnyNodesColor(nodes, "color") || hasAnyNodesColor(nodes, "backgroundColor");
    };
}

export class FormatPlugin extends Plugin {
    static name = "format";
    static dependencies = ["selection", "split", "delete"];
    // TODO ABD: refactor to handle Knowledge comments inside this plugin without sharing mergeAdjacentInlines.
    static shared = ["isSelectionFormat", "insertAndSelectZws", "mergeAdjacentInlines"];
    resources = {
        shortcuts: [
            { hotkey: "control+b", command: "FORMAT_BOLD" },
            { hotkey: "control+i", command: "FORMAT_ITALIC" },
            { hotkey: "control+u", command: "FORMAT_UNDERLINE" },
            { hotkey: "control+5", command: "FORMAT_STRIKETHROUGH" },
        ],
        toolbarCategory: withSequence(20, { id: "decoration" }),
        toolbarItems: [
            {
                id: "bold",
                category: "decoration",
                action(dispatch) {
                    dispatch("FORMAT_BOLD");
                },
                icon: "fa-bold",
                title: _t("Toggle bold"),
                isFormatApplied: isFormatted(this, "bold"),
            },
            {
                id: "italic",
                category: "decoration",
                action(dispatch) {
                    dispatch("FORMAT_ITALIC");
                },
                icon: "fa-italic",
                title: _t("Toggle italic"),
                isFormatApplied: isFormatted(this, "italic"),
            },
            {
                id: "underline",
                category: "decoration",
                action(dispatch) {
                    dispatch("FORMAT_UNDERLINE");
                },
                icon: "fa-underline",
                title: _t("Toggle underline"),
                isFormatApplied: isFormatted(this, "underline"),
            },
            {
                id: "strikethrough",
                category: "decoration",
                action(dispatch) {
                    dispatch("FORMAT_STRIKETHROUGH");
                },
                icon: "fa-strikethrough",
                title: _t("Toggle strikethrough"),
                isFormatApplied: isFormatted(this, "strikeThrough"),
            },
            {
                id: "remove_format",
                category: "decoration",
                action(dispatch) {
                    dispatch("FORMAT_REMOVE_FORMAT");
                },
                icon: "fa-eraser",
                title: _t("Remove Format"),
                hasFormat: hasFormat(this),
            },
        ],
        arrows_should_skip: (ev, char, lastSkipped) => char === "\u200b",
        onBeforeInput: withSequence(20, this.onBeforeInput.bind(this)),
    };

    handleCommand(command, payload) {
        switch (command) {
            case "FORMAT_BOLD":
                this.formatSelection("bold");
                break;
            case "FORMAT_ITALIC":
                this.formatSelection("italic");
                break;
            case "FORMAT_UNDERLINE":
                this.formatSelection("underline");
                break;
            case "FORMAT_STRIKETHROUGH":
                this.formatSelection("strikeThrough");
                break;
            case "FORMAT_FONT_SIZE":
                this.formatSelection("fontSize", {
                    applyStyle: true,
                    formatProps: { size: payload.size },
                });
                break;
            case "FORMAT_FONT_SIZE_CLASSNAME":
                this.formatSelection("setFontSizeClassName", {
                    formatProps: { className: payload.className },
                });
                break;
            case "FORMAT_REMOVE_FORMAT":
                this.removeFormat();
                break;
            case "CLEAN_FOR_SAVE": {
                this.cleanForSave(payload);
                break;
            }
            case "NORMALIZE":
                this.normalize(payload.node);
                break;
        }
    }

    removeFormat() {
        for (const format of Object.keys(formatsSpecs)) {
            if (!formatsSpecs[format].removeStyle || !this.hasSelectionFormat(format)) {
                continue;
            }
            this._formatSelection(format, { applyStyle: false });
        }
        for (const callback of this.getResource("removeFormat")) {
            callback();
        }
        this.dispatch("ADD_STEP");
    }

    /**
     * Return true if the current selection on the editable contain a formated
     * node
     *
     * @param {Element} editable
     * @param {String} format 'bold'|'italic'|'underline'|'strikeThrough'|'switchDirection'
     * @returns {boolean}
     */
    hasSelectionFormat(format) {
        const selectedNodes = this.shared.getTraversedNodes().filter(isTextNode);
        const isFormatted = formatsSpecs[format].isFormatted;
        return selectedNodes.some((n) => isFormatted(n, this.editable));
    }
    /**
     * Return true if the current selection on the editable appears as the
     * given
     * format. The selection is considered to appear as that format if every
     * text node in it appears as that format.
     *
     * @param {Element} editable
     * @param {String} format 'bold'|'italic'|'underline'|'strikeThrough'|'switchDirection'
     * @returns {boolean}
     */
    isSelectionFormat(format, traversedNodes = this.shared.getTraversedNodes()) {
        const selectedNodes = traversedNodes.filter(isTextNode);
        const isFormatted = formatsSpecs[format].isFormatted;
        return selectedNodes.length && selectedNodes.every((n) => isFormatted(n, this.editable));
    }

    formatSelection(...args) {
        if (this._formatSelection(...args)) {
            this.dispatch("ADD_STEP");
        }
    }

    // @todo phoenix: refactor this method.
    _formatSelection(formatName, { applyStyle, formatProps } = {}) {
        // note: does it work if selection is in opposite direction?
        const selection = this.shared.splitSelection();
        if (typeof applyStyle === "undefined") {
            applyStyle = !this.isSelectionFormat(formatName);
        }

        let zws;
        if (selection.isCollapsed) {
            if (isTextNode(selection.anchorNode) && selection.anchorNode.textContent === "\u200b") {
                zws = selection.anchorNode;
                this.shared.setSelection({
                    anchorNode: zws,
                    anchorOffset: 0,
                    focusNode: zws,
                    focusOffset: 1,
                });
            } else {
                zws = this.insertAndSelectZws();
            }
        }

        // Get selected nodes within td to handle non-p elements like h1, h2...
        // Targeting <br> to ensure span stays inside its corresponding block node.
        const selectedNodesInTds = [...this.editable.querySelectorAll(".o_selected_td")].map(
            (node) => node.querySelector("br")
        );
        const selectedNodes = /** @type { Text[] } **/ (
            this.shared
                .getSelectedNodes()
                .filter(
                    (n) =>
                        isTextNode(n) && isContentEditable(n) && (isVisibleTextNode(n) || isZWS(n))
                )
        );
        const selectedTextNodes = selectedNodes.length ? selectedNodes : selectedNodesInTds;

        const selectedFieldNodes = new Set(
            this.shared
                .getSelectedNodes()
                .map((n) => closestElement(n, "*[t-field],*[t-out],*[t-esc]"))
                .filter(Boolean)
        );
        const formatSpec = formatsSpecs[formatName];
        for (const selectedTextNode of selectedTextNodes) {
            const inlineAncestors = [];
            /** @type { Node } */
            let currentNode = selectedTextNode;
            let parentNode = selectedTextNode.parentElement;

            // Remove the format on all inline ancestors until a block or an element
            // with a class that is not related to font size (in case the formatting
            // comes from the class).

            while (
                parentNode &&
                !isBlock(parentNode) &&
                !this.shared.isUnsplittable(parentNode) &&
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
                    const newLastAncestorInlineFormat = this.shared.splitAroundUntil(
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
                    formatSpec.addNeutralStyle(getOrCreateSpan(selectedTextNode, inlineAncestors));
            } else if (!firstBlockOrClassHasFormat && applyStyle) {
                const tag = formatSpec.tagName && this.document.createElement(formatSpec.tagName);
                if (tag) {
                    selectedTextNode.after(tag);
                    tag.append(selectedTextNode);

                    if (!formatSpec.isFormatted(tag, formatProps)) {
                        tag.after(selectedTextNode);
                        tag.remove();
                        formatSpec.addStyle(
                            getOrCreateSpan(selectedTextNode, inlineAncestors),
                            formatProps
                        );
                    }
                } else if (formatName !== "fontSize" || formatProps.size !== undefined) {
                    formatSpec.addStyle(
                        getOrCreateSpan(selectedTextNode, inlineAncestors),
                        formatProps
                    );
                }
            }
        }

        for (const selectedFieldNode of selectedFieldNodes) {
            if (applyStyle) {
                formatSpec.addStyle(selectedFieldNode, formatProps);
            } else {
                formatSpec.removeStyle(selectedFieldNode);
            }
        }

        if (zws) {
            const siblings = [...zws.parentElement.childNodes];
            if (
                !isBlock(zws.parentElement) &&
                selectedTextNodes.includes(siblings[0]) &&
                selectedTextNodes.includes(siblings[siblings.length - 1])
            ) {
                zws.parentElement.setAttribute("data-oe-zws-empty-inline", "");
            } else {
                const span = this.document.createElement("span");
                span.setAttribute("data-oe-zws-empty-inline", "");
                zws.before(span);
                span.append(zws);
            }
        }

        if (selectedTextNodes[0] && selectedTextNodes[0].textContent === "\u200B") {
            this.shared.setCursorStart(selectedTextNodes[0]);
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
            this.shared.setSelection(newSelection, { normalize: false });
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
            this.cleanElement(element, { preserveSelection });
        }
        this.mergeAdjacentInlines(root, { preserveSelection });
    }

    cleanElement(element, { preserveSelection }) {
        delete element.dataset.oeZwsEmptyInline;
        if (!allWhitespaceRegex.test(element.textContent)) {
            // The element has some meaningful text. Remove the ZWS in it.
            this.cleanZWS(element, { preserveSelection });
            return;
        }
        if (this.getResource("isUnremovable").some((predicate) => predicate(element))) {
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
        const cursors = preserveSelection ? this.shared.preserveSelection() : null;
        for (const node of textNodes) {
            cleanTextNode(node, "\u200B", cursors);
        }
        cursors?.restore();
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

    onBeforeInput(ev) {
        if (ev.inputType === "insertText") {
            const selection = this.shared.getEditableSelection();
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
                this.shared.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
            }
        }
    }

    mergeAdjacentInlines(root, { preserveSelection = true } = {}) {
        let selectionToRestore = null;
        for (const node of descendants(root)) {
            if (this.shouldBeMergedWithPreviousSibling(node)) {
                if (preserveSelection) {
                    selectionToRestore ??= this.shared.preserveSelection();
                    selectionToRestore.update(callbacksForCursorUpdate.merge(node));
                }
                node.previousSibling.append(...childNodes(node));
                node.remove();
            }
        }
        selectionToRestore?.restore();
    }

    shouldBeMergedWithPreviousSibling(node) {
        return (
            !isSelfClosingElement(node) &&
            areSimilarElements(node, node.previousSibling) &&
            !this.shared.isUnmergeable(node)
        );
    }
}

function getOrCreateSpan(node, ancestors) {
    const document = node.ownerDocument;
    const span = ancestors.find((element) => element.tagName === "SPAN" && element.isConnected);
    if (span) {
        return span;
    } else {
        const span = document.createElement("span");
        node.after(span);
        span.append(node);
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
        const attributesNames = node.getAttributeNames().filter((name) => {
            return name !== "data-oe-zws-empty-inline";
        });
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
