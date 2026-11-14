import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { isBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { childNodes, closestElement } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

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

const PRESERVED_CLASSNAMES = new Set(["o_mail_redirect", "o-discuss-mention"]);

/**
 * This plugin works with the composer used in Discuss, ChatWindow and Chatter.
 * For the full composer, it is using HtmlComposerMessageField.
 */
export class MailComposerPlugin extends Plugin {
    static id = "mail_composer";
    static dependencies = ["clipboard", "dom", "hint", "history", "input", "selection", "split"];
    /** @type {HTMLLIElement|null} */
    listItemFromShorthand = null;
    resources = {
        on_will_paste_handlers: this.config.composerPluginDependencies.onBeforePaste.bind(this),
        paste_odoo_editor_html_overrides: this.handlePasteHtmlOverride.bind(this),
        should_bypass_paste_image_files_predicates: () => true,
        on_link_created_handlers: (linkEl) => (linkEl.target = "_blank"),
        hints: [
            withSequence(1, {
                selector: `.odoo-editor-editable > ${baseContainerGlobalSelector}:only-child`,
                text: this.config.placeholder,
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
        on_input_handlers: [
            this.config.composerPluginDependencies.onInput.bind(this),
            // after the shorthands, which turn "- " into a list
            withSequence(20, this.rememberListItemFromShorthand.bind(this)),
        ],
        insert_line_break_element_overrides: this.splitListItemOnLineBreak.bind(this),
        // before the list plugin, which removes the bullet
        delete_backward_overrides: withSequence(5, this.undoListFromShorthand.bind(this)),
    };

    setup() {
        this.addDomListener(
            this.editable,
            "keydown",
            this.config.composerPluginDependencies.onKeydown
        );
        this.addDomListener(
            this.editable,
            "focusin",
            this.config.composerPluginDependencies.onFocusin
        );
        this.addDomListener(
            this.editable,
            "focusout",
            this.config.composerPluginDependencies.onFocusout
        );
    }
    handlePasteHtmlOverride(selection, sanitizedFragment) {
        if (sanitizedFragment.childNodes.length === 0) {
            return false;
        }
        const removeStyle = (node, keepLineBreaks = false) => {
            if (node.nodeType === Node.TEXT_NODE) {
                if (keepLineBreaks) {
                    node.replaceWith(...splitLines(node.textContent));
                }
                return;
            }
            if (node.nodeType === Node.ELEMENT_NODE) {
                const tagName = node.nodeName.toUpperCase();
                if (tagName === "BR") {
                    return;
                }
                if (!ALLOWED_TAGS.includes(tagName)) {
                    node.replaceWith(...getTextLines(node, keepLineBreaks));
                    return;
                }
                keepLineBreaks ||= keepsLineBreaks(node);
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
                [...node.childNodes].forEach((child) => removeStyle(child, keepLineBreaks));
            }
        };
        [...sanitizedFragment.childNodes].forEach((node) => removeStyle(node));
        flattenStructuralDivWrappers(sanitizedFragment);
        this.dependencies.dom.insert(sanitizedFragment);
        this.dependencies.history.commit();
        return true;
    }

    /**
     * Enter can send the message, so Shift+Enter in a list item acts as Enter does in a document:
     * it adds an item, or leaves the list when the item is empty.
     *
     * @param {{ targetNode: Node, targetOffset: number }} params
     */
    splitListItemOnLineBreak({ targetNode, targetOffset }) {
        if (!closestElement(targetNode, "LI")) {
            return;
        }
        this.dependencies.split.splitBlockNode({ targetNode, targetOffset });
        return true;
    }

    /**
     * A space that leaves the caret in an empty item has just turned a shorthand into a list.
     *
     * @param {InputEvent} ev
     */
    rememberListItemFromShorthand(ev) {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const li = closestElement(anchorNode, "LI");
        this.listItemFromShorthand = ev.data === " " && li && !li.textContent ? li : null;
    }

    /**
     * Backspace right after a list shorthand gives back the typed text, e.g. to start with "- ".
     *
     * @param {{ startContainer: Node, startOffset: number, endContainer: Node, endOffset: number }} range
     */
    undoListFromShorthand({ startContainer, startOffset, endContainer, endOffset }) {
        const li = this.listItemFromShorthand;
        this.listItemFromShorthand = null;
        if (
            !li?.isConnected ||
            li.textContent ||
            startContainer !== endContainer ||
            startOffset !== endOffset ||
            closestElement(startContainer, "LI") !== li
        ) {
            return;
        }
        this.dependencies.history.undo();
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

/**
 * The text of the node, like `textContent`, with its kept line breaks as `<br>`.
 *
 * @param {Node} node
 * @param {boolean} keepLineBreaks whether the node is inside an element that keeps them
 */
function getTextLines(node, keepLineBreaks) {
    if (node.nodeType === Node.TEXT_NODE) {
        return keepLineBreaks ? splitLines(node.textContent) : [node.textContent];
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return [];
    }
    if (node.nodeName === "BR") {
        return [node];
    }
    keepLineBreaks ||= keepsLineBreaks(node);
    return [...node.childNodes].flatMap((child) => getTextLines(child, keepLineBreaks));
}

/**
 * Whether the line breaks of the element's text are displayed: in a `<pre>`, or
 * with the `white-space` that browsers inline on copied code.
 *
 * @param {Element} el
 */
function keepsLineBreaks(el) {
    const whiteSpace = el.style?.whiteSpace;
    return el.nodeName === "PRE" || (!!whiteSpace && !["normal", "nowrap"].includes(whiteSpace));
}

/**
 * The lines of the text between `<br>`, keeping its runs of spaces and tabs as alternating nbsp.
 *
 * @param {string} text
 */
function splitLines(text) {
    return text
        .split(/\r\n|\r|\n/)
        .map((line) =>
            line
                .replace(/\t/g, "    ")
                .replace(/ {2,}/g, (spaces) =>
                    spaces.replace(/ /g, (space, index) => (index % 2 ? space : "\u00A0"))
                )
        )
        .flatMap((line, index) => (index ? [document.createElement("br"), line] : [line]))
        .filter(Boolean);
}
