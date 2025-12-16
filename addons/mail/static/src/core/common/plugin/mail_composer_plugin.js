import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";
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

/**
 * This plugin works with the composer used in Discuss, ChatWindow and Chatter.
 * For the full composer, it is using HtmlComposerMessageField.
 */
export class MailComposerPlugin extends Plugin {
    static id = "mail_composer";
    static dependencies = ["clipboard", "dom", "hint", "history", "input", "selection"];
    resources = {
        before_paste_handlers: this.config.composerPluginDependencies.onBeforePaste.bind(this),
        bypass_paste_image_files: () => true,
        create_link_handlers: (linkEl) => (linkEl.target = "_blank"),
        hints: [
            withSequence(1, {
                selector: `.odoo-editor-editable > ${baseContainerGlobalSelector}:only-child`,
                text: this.config.placeholder,
            }),
        ],
        handle_paste_html_override: this.handlePasteHtmlOverride.bind(this),
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
        input_handlers: this.config.composerPluginDependencies.onInput.bind(this),
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
    handlePasteHtmlOverride(sanitizedFragment) {
        if (
            this.config.composerPluginDependencies.isInChatter ||
            sanitizedFragment.childNodes.length === 0
        ) {
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
                node.removeAttribute("class");
                // Recursively sanitize child nodes
                [...node.childNodes].forEach(removeStyle);
            }
        };
        [...sanitizedFragment.childNodes].forEach(removeStyle);
        this.dependencies.dom.insert(sanitizedFragment);
        this.dependencies.history.addStep();
        return true;
    }
}
