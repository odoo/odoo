import { Plugin } from "@html_editor/plugin";
import { CodeToolbar } from "./code_toolbar";
import { renderToElement } from "@web/core/utils/render";

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
    resources = {
        mount_component_handlers: this.setupNewCodeBlock.bind(this),
        normalize_handlers: (root) => this.addCodeBlocks(root, true),
        post_undo_handlers: () => this.addCodeBlocks(this.editable, true),
        post_redo_handlers: () => this.addCodeBlocks(this.editable, true),
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
        // Ensure focus can be preserved within the textarea:
        is_node_editable_predicates: (node) => node?.classList?.contains("o_prism_source"),
        bypass_fix_selection_on_editable_root_predicates: ({ documentSelection }) =>
            // If the document selection is targeting the textarea, don't
            // change it so we can keep the focus in the textarea.
            documentSelection.isCollapsed &&
            this.document.activeElement?.nodeName === "TEXTAREA" &&
            documentSelection.anchorNode?.matches?.(CODE_BLOCK_SELECTOR) &&
            documentSelection.anchorOffset === 1,
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.codeToolbar = this.dependencies.overlay.createOverlay(CodeToolbar, {
            positionOptions: {
                position: "top-fit",
                flip: false,
            },
            closeOnPointerdown: false,
        });
        this.addDomListener(this.document, "scroll", this.codeToolbar.close, true);
        this.addCodeBlocks();
    }

    cleanForSave(root) {
        // Do not save the embedded props, so we can recompute them on load.
        for (const codeBlock of root.querySelectorAll("div.o_syntax_highlighting")) {
            codeBlock.removeAttribute("data-embedded-props");
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
            const codeBlock = renderToElement("html_editor.EmbeddedSyntaxHighlightingBlueprint", {
                embeddedProps: JSON.stringify({
                    initialValue: this.getPreValue(pre),
                    focusTextarea:
                        preserveFocus && !targetedNodes.some((node) => !pre.contains(node)),
                }),
            });
            pre.before(codeBlock);
            pre.remove();
        }
    }

    /**
     * Return the given `<pre>` element's inner text, cleaned of any zero-width
     * characters or trailing invisible newline characters (a trailing `<br>` in
     * the element's HTML is invisible but results in an visible `\n` in its
     * `innerText` property, which would be visible if kept).
     *
     * @param {HTMLPreElement} pre
     * @returns {string}
     */
    getPreValue(pre) {
        // Trailing br gives \n in innerText but should not be visible.
        const trailingBrs = pre.innerHTML.match(/(<br>)+$/)?.length || 0;
        return pre.innerText
            .slice(0, pre.innerText.length - (trailingBrs > 1 ? trailingBrs - 1 : trailingBrs))
            .replace(/[\u200B\uFEFF]/g, "");
    }

    setupNewCodeBlock({ name, props }) {
        if (name === "syntaxHighlighting") {
            let initialValue = props.initialValue || "";
            if (props.host.hasAttribute("data-syntax-highlighting-value")) {
                // Preserve any saved value as initial value of the current
                // editing session.
                initialValue = props.host.dataset.syntaxHighlightingValue;
            }
            Object.assign(props, {
                codeToolbar: this.codeToolbar,
                focusTextarea: props.focusTextarea || false,
                initialValue,
                onTextareaFocus: () => this.dependencies.history.stageFocus(),
                getPreValue: (pre) => this.getPreValue(pre),
                addHistoryStep: () => this.dependencies.history.addStep(),
            });
        }
    }
}
