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

const CODE_BLOCK_CLASS = "o_syntax_highlighting";
const CODE_BLOCK_SELECTOR = `div.${CODE_BLOCK_CLASS}`;

export class SyntaxHighlightingPlugin extends Plugin {
    static id = "syntaxHighlighting";
    static dependencies = [
        "baseContainer",
        "overlay",
        "history",
        "selection",
        "protectedNode",
        "embeddedComponents",
    ];
    static defaultConfig = {
        syntaxHighlightingTextLimit: 1_000_000,
    };
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
        on_will_mount_component_handlers: this.setupNewCodeBlock.bind(this),
        on_undone_handlers: () => this.addCodeBlocks(this.editable, true),
        on_redone_handlers: () => this.addCodeBlocks(this.editable, true),
        on_will_set_tag_handlers: (el, newTagName, cursors) => {
            if (newTagName.toLowerCase() === "pre") {
                // Remove invisible whitespace that would become visible in a `<pre>` element.
                removeInvisibleWhitespace(el, cursors);
            }
        },

        /** Processors */
        clean_for_save_processors: withSequence(0, (root) => this.cleanForSave(root)),
        normalize_processors: (root) => this.addCodeBlocks(root, true),
        clipboard_content_processors: (clonedContent) => this.cleanForSave(clonedContent),
    };

    setup() {
        this.addCodeBlocks();
        this.addDomListener(this.editable, "keydown", (ev) => {
            const arrowHandled = ["arrowup", "control+arrowup", "arrowdown", "control+arrowdown"];
            if (arrowHandled.includes(getActiveHotkey(ev))) {
                this.navigateAroundCodeBlock(ev);
            }
        });
    }

    navigateAroundCodeBlock(ev) {
        const isArrowUp = ev.key === "ArrowUp";
        const selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        if (!selection.isCollapsed) {
            return;
        }
        const anchorNode = selection.anchorNode;
        const currentBlock = closestBlock(anchorNode);
        const adjacentBlock = isArrowUp
            ? currentBlock.previousElementSibling
            : currentBlock.nextElementSibling;
        if (!adjacentBlock?.matches(CODE_BLOCK_SELECTOR)) {
            return;
        }

        const actualSelection = this.document.getSelection();
        const preserveSelection = this.dependencies.selection.preserveSelection();
        actualSelection.modify("extend", isArrowUp ? "backward" : "forward", "line");
        const reachedBlock = closestBlock(actualSelection.focusNode);
        preserveSelection.restore();

        // If extending the selection reaches another block, the cursor
        // is at the block boundary.
        if (currentBlock !== reachedBlock) {
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
            if (!pre) {
                continue;
            }
            pre.dataset.embedded = "readonlySyntaxHighlighting"; // Make it work in readonly.
            const embeddedProps = getEmbeddedProps(codeBlock);
            const value = embeddedProps.value;
            pre.dataset.languageId = embeddedProps.languageId;
            if (embeddedProps.codeWrap) {
                pre.setAttribute("data-code-wrap", "");
            }
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
            // Do not convert large <pre> elements into syntax-highlighted
            // components. If the content exceeds the defined limit, original
            // <pre> is preserved to avoid performance issues.
            if (pre.textContent.length > this.config.syntaxHighlightingTextLimit) {
                continue;
            }
            const isPreInSelection = !targetedNodes.some((node) => !pre.contains(node));
            const embeddedProps = JSON.stringify(
                Object.assign(
                    {
                        value: getPreValue(pre),
                        languageId: pre.dataset.languageId || DEFAULT_LANGUAGE_ID,
                    },
                    pre.hasAttribute("data-code-wrap") ? { codeWrap: true } : {}
                )
            );
            const codeBlock = this.dependencies.embeddedComponents.renderBlueprintToElement(
                "html_editor.EmbeddedSyntaxHighlightingBlueprint",
                { embeddedProps, isCodeWrap: pre.hasAttribute("data-code-wrap") },
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
                convertToParagraph: ({ target }) => {
                    this.dependencies.history.stageSelection();
                    const component = target.closest(`[data-embedded='${name}']`);
                    const embeddedProps = getEmbeddedProps(component);
                    const baseContainer = this.dependencies.baseContainer.createBaseContainer({
                        children: [this.document.createTextNode(embeddedProps.value)],
                    });
                    component.replaceWith(baseContainer);
                    newlinesToLineBreaks(baseContainer);
                    this.dependencies.selection.setCursorStart(baseContainer);
                    this.dependencies.history.addStep();
                },
                setSelection: (selection) => this.dependencies.selection.setSelection(selection),
            });
            props.host.removeAttribute("data-syntax-highlighting-autofocus");
        }
    }
}
