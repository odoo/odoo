import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import {
    DEFAULT_LANGUAGE_ID,
    getPreValue,
    newlinesToLineBreaks,
} from "../../core/syntax_highlighting/syntax_highlighting_utils";
import { removeInvisibleWhitespace } from "@html_editor/utils/dom";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { closestBlock } from "@html_editor/utils/blocks";
import { closestElement, createDOMPathGenerator } from "@html_editor/utils/dom_traversal";
import { DIRECTIONS } from "@html_editor/utils/position";
import { isEmpty } from "@html_editor/utils/dom_info";

const CODE_BLOCK_CLASS = "o_syntax_highlighting";
const CODE_BLOCK_SELECTOR = `div.${CODE_BLOCK_CLASS}`;

export class SyntaxHighlightingPlugin extends Plugin {
    static id = "syntaxHighlighting";
    static dependencies = [
        "overlay",
        "history",
        "selection",
        "protectedNode",
        "embeddedComponents",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        // Ensure focus can be preserved within the textarea:
        is_node_editable_predicates: (node) => {
            if (node?.classList?.contains("o_prism_source")) {
                return true;
            }
        },
        system_attributes: "data-syntax-highlighting-autofocus",

        /** Handlers */
        mount_component_handlers: this.setupNewCodeBlock.bind(this),
        normalize_handlers: (root) => this.addCodeBlocks(root, true),
        post_undo_handlers: () => this.addCodeBlocks(this.editable, true),
        post_redo_handlers: () => this.addCodeBlocks(this.editable, true),
        clean_for_save_handlers: withSequence(0, ({ root }) => this.cleanForSave(root)),
        before_set_tag_handlers: (el, newTagName, cursors) => {
            if (newTagName.toLowerCase() === "pre") {
                // Remove invisible whitespace that would become visible in a `<pre>` element.
                removeInvisibleWhitespace(el, cursors);
            }
        },

        /** Processors */
        clipboard_content_processors: (clonedContent) => this.cleanForSave(clonedContent),
    };

    setup() {
        this.addCodeBlocks();
        this.addDomListener(this.editable, "keydown", (ev) => {
            const arrowHandled = ["arrowup", "control+arrowup", "arrowdown", "control+arrowdown"];
            if (arrowHandled.includes(getActiveHotkey(ev))) {
                this.navigateCodeBlock(ev);
            }
        });
    }

    navigateCodeBlock(ev) {
        const isArrowUp = ev.key === "ArrowUp";
        const selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        if (!selection.isCollapsed) {
            return;
        }
        const anchorNode = selection.anchorNode;
        const blockEl = closestBlock(anchorNode);
        const adjacentBlock = isArrowUp
            ? blockEl.previousElementSibling
            : blockEl.nextElementSibling;
        if (!adjacentBlock || !adjacentBlock.matches(CODE_BLOCK_SELECTOR)) {
            return;
        }
        let shouldNavigate = true;
        if (!isEmpty(blockEl)) {
            const closestEl = closestElement(anchorNode);
            const currentNode =
                anchorNode === closestEl
                    ? closestEl.childNodes[selection.anchorOffset]
                    : anchorNode;
            const direction = isArrowUp ? DIRECTIONS.LEFT : DIRECTIONS.RIGHT;
            const domPath = createDOMPathGenerator(direction, {
                leafOnly: true,
                stopTraverseFunction: (node) => node === blockEl,
                stopFunction: (node) => node === blockEl,
            });
            const domPathNode = domPath(currentNode);
            let node = domPathNode.next().value;
            if (currentNode.nodeName === "BR" && node) {
                shouldNavigate = false;
            } else {
                while (node) {
                    if (node.nodeName === "BR") {
                        shouldNavigate = false;
                        break;
                    }
                    node = domPathNode.next().value;
                }
            }
        }
        if (shouldNavigate) {
            ev.preventDefault();
            const textarea = adjacentBlock.querySelector("textarea");
            const position = isArrowUp ? textarea.value.length : 0;
            textarea.focus({ preventScroll: true });
            textarea.setSelectionRange(position, position);
        }
    }

    cleanForSave(root) {
        for (const codeBlock of root.querySelectorAll("div.o_syntax_highlighting")) {
            // Save only the `<pre>` element, with information to rebuild the
            // embedded component, so the saved DOM is independent of this plugin.
            const pre = codeBlock.querySelector("pre");
            pre.dataset.embedded = "readonlySyntaxHighlighting"; // Make it work in readonly.
            const embeddedProps = getEmbeddedProps(codeBlock);
            const value = embeddedProps.value;
            pre.dataset.languageId = embeddedProps.languageId;
            codeBlock.before(pre);
            codeBlock.remove();
            // Remove highlighting.
            pre.textContent = value;
            newlinesToLineBreaks(pre);
        }
    }

    /**
     * Take all `<pre>` element in the given `root` that aren't in an embedded
     * syntax highlighting block, and replace them with an embedded syntax
     * highlighting block. If `preserveFocus` is true, set the currently
     * targeted `<pre>` element to be focused.
     *
     * @param {Element} [root = this.editable]
     * @param {boolean} [preserveFocus = false]
     */
    addCodeBlocks(root = this.editable, preserveFocus = false) {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        const nonEmbeddedPres = [...root.querySelectorAll("pre")].filter(
            (pre) => !pre.closest(CODE_BLOCK_SELECTOR)
        );
        for (const pre of nonEmbeddedPres) {
            const isPreInSelection = !targetedNodes.some((node) => !pre.contains(node));
            const embeddedProps = JSON.stringify({
                value: getPreValue(pre),
                languageId: pre.dataset.languageId || DEFAULT_LANGUAGE_ID,
            });
            const codeBlock = this.dependencies.embeddedComponents.renderBlueprintToElement(
                "html_editor.EmbeddedSyntaxHighlightingBlueprint",
                { embeddedProps },
                () => {
                    if (preserveFocus && isPreInSelection) {
                        const textarea = codeBlock.querySelector("textarea");
                        if (textarea !== codeBlock.ownerDocument.activeElement) {
                            textarea.focus();
                            this.dependencies.history.stageFocus();
                        }
                    }
                }
            );
            pre.before(codeBlock);
            if (isPreInSelection) {
                // Removing the pre will make us lose the selection. The DOM
                // would try to set it in the root, which would get corrected,
                // preventing us from directly writing inside the textarea.
                this.document.getSelection().removeAllRanges();
            }
            pre.remove();
        }
    }

    setupNewCodeBlock({ name, props }) {
        if (name === "syntaxHighlighting") {
            Object.assign(props, {
                onTextareaFocus: () => this.dependencies.history.stageFocus(),
                setCursorStart: (el) => this.dependencies.selection.setCursorStart(el),
                setCursorEnd: (el) => this.dependencies.selection.setCursorEnd(el),
            });
            props.host.removeAttribute("data-syntax-highlighting-autofocus");
        }
    }
}
