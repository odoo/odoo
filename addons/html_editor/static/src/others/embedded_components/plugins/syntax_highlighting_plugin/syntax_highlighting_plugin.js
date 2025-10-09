import { Plugin } from "@html_editor/plugin";
import { CodeToolbar } from "./code_toolbar";
import { renderToElement } from "@web/core/utils/render";
import { withSequence } from "@html_editor/utils/resource";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import {
    DEFAULT_LANGUAGE_ID,
    getPreValue,
    newlinesToLineBreaks,
} from "../../core/syntax_highlighting/syntax_highlighting_utils";

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
        mount_component_handlers: this.setupNewCodeBlock.bind(this),
        normalize_handlers: (root) => this.addCodeBlocks(root, true),
        post_undo_handlers: () => this.addCodeBlocks(this.editable, true),
        post_redo_handlers: () => this.addCodeBlocks(this.editable, true),
        clean_for_save_handlers: withSequence(0, ({ root }) => this.cleanForSave(root)),
        // Ensure focus can be preserved within the textarea:
        is_node_editable_predicates: (node) => {
            if (node?.classList?.contains("o_prism_source")) {
                return true;
            }
        },
        system_attributes: "data-syntax-highlighting-autofocus",
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
        for (const codeBlock of root.querySelectorAll("div.o_syntax_highlighting")) {
            // Save only the `<pre>` element, with information to rebuild the
            // embedded component, so the saved DOM is independent of this plugin.
            const pre = codeBlock.querySelector("pre");
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
            const codeBlock = renderToElement("html_editor.EmbeddedSyntaxHighlightingBlueprint", {
                embeddedProps: JSON.stringify({
                    value: getPreValue(pre),
                    languageId: pre.dataset.languageId || DEFAULT_LANGUAGE_ID,
                }),
            });
            codeBlock.dataset.syntaxHighlightingAutofocus = preserveFocus && isPreInSelection;
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
                codeToolbar: this.codeToolbar,
                autofocus: props.host.dataset.syntaxHighlightingAutofocus === "true",
                onTextareaFocus: () => this.dependencies.history.stageFocus(),
            });
            props.host.removeAttribute("data-syntax-highlighting-autofocus");
        }
    }
}
