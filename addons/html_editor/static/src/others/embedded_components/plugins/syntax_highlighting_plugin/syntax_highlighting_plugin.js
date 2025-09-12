import { Plugin } from "@html_editor/plugin";
import { CodeToolbar } from "./code_toolbar";
import { renderToElement } from "@web/core/utils/render";
import { withSequence } from "@html_editor/utils/resource";
import { descendants, lastLeaf } from "@html_editor/utils/dom_traversal";
import { fillEmpty } from "@html_editor/utils/dom";

const CODE_BLOCK_CLASS = "o_syntax_highlighting";
const CODE_BLOCK_SELECTOR = `div.${CODE_BLOCK_CLASS}`;

export const newlinesToLineBreaks = (element, doc = element.ownerDocument || document) => {
    // 1. Replace \n with <br>.
    for (const node of descendants(element).filter((node) => node.nodeType === Node.TEXT_NODE)) {
        let newline = node.textContent.indexOf("\n");
        while (newline !== -1) {
            node.before(doc.createTextNode(node.textContent.slice(0, newline)));
            node.before(doc.createElement("BR"));
            node.textContent = node.textContent.slice(newline + 1);
            newline = node.textContent.indexOf("\n");
        }
        if (!node.textContent) {
            node.remove(); // Prevent empty trailing text node that would become the last leaf.
        }
    }
    // 2. Handle trailing BRs. Eg, <span>ab\n</span> -> <span>ab</span><br><br>
    const trailingBr = lastLeaf(element);
    if (trailingBr?.nodeName === "BR") {
        element.append(trailingBr); // <span>ab<br></span> -> <span>ab</span><br>
        trailingBr.after(doc.createElement("BR")); // <br></pre> -> <br><br></pre>
    }
    // 3. Fill empty.
    fillEmpty(element);
};

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
        clean_for_save_handlers: withSequence(0, ({ root }) => this.cleanForSave(root)),
        // Ensure focus can be preserved within the textarea:
        is_node_editable_predicates: (node) => {
            if (node?.classList?.contains("o_prism_source")) {
                return true;
            }
        },
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
            const value = codeBlock.dataset.syntaxHighlightingValue;
            pre.dataset.languageId = codeBlock.dataset.languageId;
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
                    initialValue: this.getPreValue(pre),
                    autofocus: preserveFocus && isPreInSelection,
                }),
            });
            // Transfer the data from the `<pre>` element back to the embedded
            // component (see `cleanForSave`).
            if (pre.hasAttribute("data-language-id")) {
                codeBlock.dataset.languageId = pre.dataset.languageId;
            }
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
                autofocus: props.autofocus || false,
                initialValue,
                onTextareaFocus: () => this.dependencies.history.stageFocus(),
                getPreValue: (pre) => this.getPreValue(pre),
                addHistoryStep: () => this.dependencies.history.addStep(),
            });
        }
    }
}
