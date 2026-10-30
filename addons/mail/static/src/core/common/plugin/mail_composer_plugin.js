import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { getDeepestPosition, isEmptyBlock } from "@html_editor/utils/dom_info";
import { childNodes, closestElement, lastLeaf } from "@html_editor/utils/dom_traversal";
import { rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

const ALLOWED_TAGS = [
    "A",
    "B",
    "DIV",
    "EM",
    "I",
    "LI",
    "OL",
    "P",
    "S",
    "SPAN",
    "STRONG",
    "U",
    "UL",
];

export const PRESERVED_CLASSNAMES = new Set([
    "o_mail_redirect",
    "o_message_redirect",
    "o-discuss-mention",
]);

/**
 * This plugin works with the composer used in Discuss, ChatWindow and Chatter.
 * For the full composer, it is using HtmlComposerMessageField.
 */
export class MailComposerPlugin extends Plugin {
    static id = "mail_composer";
    static dependencies = [
        "baseContainer",
        "clipboard",
        "dom",
        "hint",
        "history",
        "input",
        "selection",
    ];
    static shared = ["cancelSelection", "insert", "setCursorEnd", "updateEditableState"];
    resources = {
        on_will_paste_handlers: this.config.composerPluginDependencies.onBeforePaste.bind(this),
        paste_odoo_editor_html_overrides: this.handlePasteHtmlOverride.bind(this),
        should_bypass_paste_image_files_predicates: () => true,
        on_link_created_handlers: (linkEl) => (linkEl.target = "_blank"),
        properties: [
            withSequence(1, {
                predicate: `.odoo-editor-editable > ${baseContainerGlobalSelector}:only-child`,
                // The placeholder can change during the composer's lifetime.
                hint: () => this.config.composerPluginDependencies.getPlaceholder(),
            }),
        ],
        hint_targets_providers: (selectionData, editable) => {
            const el = editable.firstChild;
            if (
                !selectionData.documentSelectionIsInEditable &&
                childNodes(editable).length === 1 &&
                isEmptyBlock(el) &&
                el.matches(baseContainerGlobalSelector)
            ) {
                return [el];
            } else {
                return [];
            }
        },
        on_input_handlers: this.config.composerPluginDependencies.onInput.bind(this),
        // after the mentions are made non-editable
        normalize_processors: withSequence(20, (root) => {
            if (root === this.editable) {
                this.wrapNonEditableInlineContent();
            }
            return root;
        }),
    };

    setup() {
        this.addDomListener(
            this.editable,
            "keydown",
            this.config.composerPluginDependencies.onKeydown
        );
        this.addDomListener(this.editable, "focusin", (ev) => {
            this.isSelectionCancelled = false;
            this.config.composerPluginDependencies.onFocusin(ev);
        });
        this.addDomListener(
            this.editable,
            "focusout",
            this.config.composerPluginDependencies.onFocusout
        );
    }

    /**
     * Cancels the selection, so that the next insertion appends at the end
     * instead of replacing it. It applies until the editable is focused again.
     */
    cancelSelection() {
        this.isSelectionCancelled = true;
    }

    /**
     * Inserts content at the cursor, replacing the selection.
     *
     * A cancelled selection is not replaced: the content is appended at the
     * end instead, like it is for an empty selection.
     *
     * @param {string|Node} content
     * @param {Object} [options]
     * @param {boolean} [options.replaceSelection=true] when false, inserts the
     *   content before the selection instead of replacing it
     * @param {boolean} [options.spaceBefore] inserts a space before the content,
     *   unless the cursor is at the start of its block or already after a space
     */
    insert(content, { replaceSelection = true, spaceBefore = false } = {}) {
        if (this.isSelectionCancelled) {
            this.isSelectionCancelled = false;
            this.setCursorEnd();
        } else if (!replaceSelection) {
            const { startContainer, startOffset } =
                this.dependencies.selection.getEditableSelection();
            this.dependencies.selection.setSelection({
                anchorNode: startContainer,
                anchorOffset: startOffset,
            });
        }
        if (spaceBefore && !this.isCursorAfterSpace()) {
            this.dependencies.dom.insert(" ");
        }
        this.dependencies.dom.insert(content);
        this.dependencies.history.commit();
    }

    /** Directly in the editable, a non-editable element (e.g. a mention) can't be deleted. */
    wrapNonEditableInlineContent() {
        const nonEditableEls = childNodes(this.editable).filter(
            (node) =>
                node.nodeType === Node.ELEMENT_NODE &&
                !isBlock(node) &&
                node.getAttribute("contenteditable") === "false"
        );
        for (const el of nonEditableEls) {
            if (el.parentElement !== this.editable) {
                continue; // wrapped with a previous one
            }
            let firstNode = el;
            while (firstNode.previousSibling && !isBlock(firstNode.previousSibling)) {
                firstNode = firstNode.previousSibling;
            }
            const inlineNodes = [];
            for (let node = firstNode; node && !isBlock(node); node = node.nextSibling) {
                inlineNodes.push(node);
            }
            // inserted first, so that the selection is restored in the editable
            const cursors = this.dependencies.selection.preserveSelection();
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            cursors.update(callbacksForCursorUpdate.before(firstNode, baseContainer));
            this.editable.insertBefore(baseContainer, firstNode);
            for (const node of inlineNodes) {
                cursors.update(callbacksForCursorUpdate.append(baseContainer, node));
                baseContainer.append(node);
            }
            cursors.restore();
        }
    }

    /** Whether the cursor is at the start of its block or after a whitespace. */
    isCursorAfterSpace() {
        const { startContainer, startOffset } = this.dependencies.selection.getEditableSelection();
        const [node, offset] = getDeepestPosition(startContainer, startOffset);
        const range = this.document.createRange();
        range.setStart(closestBlock(node), 0);
        range.setEnd(node, offset);
        const textBefore = range.toString().replaceAll("\u200B", "");
        return !textBefore || /\s$/.test(textBefore);
    }

    setCursorEnd() {
        const lastNode = lastLeaf(this.editable);
        if (!lastNode) {
            return;
        }
        if (!this.editable.isContentEditable) {
            // The editable is turned off (e.g. while it is readonly), so all of
            // its content is uneditable: selecting around it would select all
            // of it, and the next typed text would replace the paragraph.
            this.dependencies.selection.setCursorEnd(lastNode);
            return;
        }
        const nonEditableAncestor = closestElement(lastNode, (el) => !el.isContentEditable);
        if (nonEditableAncestor && this.editable.contains(nonEditableAncestor)) {
            const [anchorNode, anchorOffset] = rightPos(nonEditableAncestor);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        } else {
            this.dependencies.selection.setCursorEnd(lastNode);
        }
    }

    /** Turns the editable on or off, according to whether it is editable. */
    updateEditableState() {
        // `readonly` means nothing on a contenteditable: turn the editable off.
        const isEditable = this.config.composerPluginDependencies.isEditable();
        if (this.editable.getAttribute("contenteditable") === String(isEditable)) {
            return;
        }
        if (!isEditable) {
            // Turning the editable off blurs it: give the focus back after.
            this.hadEditableFocus = this.editable.getRootNode().activeElement === this.editable;
        }
        this.editable.setAttribute("contenteditable", isEditable);
        if (isEditable && this.hadEditableFocus) {
            this.hadEditableFocus = false;
            this.dependencies.selection.focusEditable();
        }
    }

    handlePasteHtmlOverride(selection, sanitizedFragment) {
        if (sanitizedFragment.childNodes.length === 0) {
            return false;
        }
        const removeStyle = (node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
                const tagName = node.nodeName.toUpperCase();
                if (tagName === "BR") {
                    return;
                }
                if (!ALLOWED_TAGS.includes(tagName)) {
                    node.replaceWith(document.createTextNode(node.textContent));
                    return;
                }
                node.removeAttribute("style");
                if (node.hasAttribute("class")) {
                    const preservedClasses = [...node.classList].filter((className) =>
                        PRESERVED_CLASSNAMES.has(className)
                    );
                    if (preservedClasses.length) {
                        node.className = preservedClasses.join(" ");
                    } else {
                        node.removeAttribute("class");
                    }
                }
                // Recursively sanitize child nodes
                [...node.childNodes].forEach(removeStyle);
            }
        };
        [...sanitizedFragment.childNodes].forEach(removeStyle);
        flattenStructuralDivWrappers(sanitizedFragment);
        this.dependencies.dom.insert(sanitizedFragment);
        this.dependencies.history.commit();
        return true;
    }
}

/**
 * Unwrap plain `<div>` wrappers that carry no attributes after sanitization
 * and contain only block-level children. Pasted content from Discuss/Owl UI
 * often produces deeply nested structural wrappers (each `<div>` only wraps
 * other blocks); they are pure noise and prevent operations like
 * backspace-merge from working across them.
 */
function flattenStructuralDivWrappers(root) {
    let changed = true;
    while (changed) {
        changed = false;
        for (const div of [...root.querySelectorAll("div")]) {
            if (
                div.attributes.length === 0 &&
                div.childNodes.length > 0 &&
                [...div.childNodes].every((child) => isBlock(child))
            ) {
                div.replaceWith(...div.childNodes);
                changed = true;
            }
        }
    }
}
