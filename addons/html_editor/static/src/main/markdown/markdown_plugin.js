import { Plugin } from "@html_editor/plugin";
import { isTextNode, isVisibleTextNode } from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { isMarkdown } from "./markdown_utils";

/**
 * Markdown support:
 * - when pasting Markdown, open the powerbox to let the user choose between
 *   converting it to formatted content or keeping it as plain text. The
 *   conversion is done by the server, so this plugin is only loaded if it is
 *   available (see `session.markdown_paste_available`).
 */
export class MarkdownPlugin extends Plugin {
    static id = "markdown";
    static dependencies = [
        "clipboard",
        "dom",
        "history",
        "powerbox",
        "properties",
        "sanitize",
        "selection",
        // The converted content needs these plugins to be handled correctly.
        "codeBlock",
        "image",
        "inlineCode",
        "link",
        "list",
        "media",
        "table",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        // Before the plugins that handle the paste themselves.
        paste_text_overrides: withSequence(5, this.handlePasteText.bind(this)),
        paste_html_overrides: withSequence(5, this.handlePasteHtml.bind(this)),
        on_pasted_handlers: this.openMarkdownPowerbox.bind(this),
        on_history_commit_undone_handlers: this.closeMarkdownPowerbox.bind(this),
        on_committed_to_history_handlers: this.cancelConversion.bind(this),
        on_remote_history_commit_applied_handlers: this.cancelConversion.bind(this),
        on_history_reset_handlers: this.cancelConversion.bind(this),
    };

    /**
     * Remember the Markdown and make a savepoint to be able to replace it once
     * it is pasted. Nothing is returned, so that the normal paste still runs.
     *
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     * @param {string} text
     */
    handlePasteText(selection, text) {
        if (isMarkdown(text)) {
            this.pastedMarkdown = {
                text,
                restoreSavepoint: this.dependencies.history.makeSavePoint(),
            };
        }
    }

    /**
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     * @param {DocumentFragment} clipboardElem
     * @param {DocumentFragment} sanitizedFragment
     * @param {DataTransfer} clipboardData
     */
    handlePasteHtml(selection, clipboardElem, sanitizedFragment, clipboardData) {
        if (!clipboardElem.querySelector(":not(p, div, br)")) {
            this.handlePasteText(selection, clipboardData.getData("text/plain"));
        }
    }

    /**
     * Once Markdown is pasted, open the powerbox to choose whether to convert
     * it. The pasted content is only replaced if it is converted.
     *
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     */
    openMarkdownPowerbox(selection) {
        const pastedMarkdown = this.pastedMarkdown;
        this.pastedMarkdown = null;
        const anchorElement = closestElement(selection.anchorNode);
        // Think of within link or pre.
        if (
            !pastedMarkdown ||
            closestElement(anchorElement, "a") ||
            !this.dependencies.properties.get(anchorElement, "powerbox", true)
        ) {
            return;
        }
        const { text, restoreSavepoint } = pastedMarkdown;
        // Start converting while the user chooses, so it's more likely to be
        // done when the command is applied.
        const htmlPromise = rpc("/html_editor/markdown_to_html", { text }).catch(() => false);
        this.dependencies.powerbox.openPowerbox({
            commands: [
                {
                    title: _t("Convert Markdown"),
                    description: _t("Paste the content with its formatting."),
                    icon: "article",
                    run: () => this.insertMarkdown(htmlPromise, restoreSavepoint),
                },
                {
                    title: _t("Paste as plain text"),
                    description: _t("Keep the Markdown syntax as text."),
                    icon: "text_fields",
                    run: () => {},
                },
            ],
            onClose: () => (this.isMarkdownPowerboxOpen = false),
        });
        this.isMarkdownPowerboxOpen = true;
    }

    /**
     * Replace the pasted text by the converted HTML once the conversion is
     * done, unless it failed or the content changed in the meantime: the text
     * is then kept. The converted HTML is standard HTML, which plugins adapt
     * to using `html_compatibility_processors` when it is inserted.
     *
     * @param {Promise<string | false>} htmlPromise
     * @param {Function} restoreSavepoint restores the content before the paste
     */
    async insertMarkdown(htmlPromise, restoreSavepoint) {
        const conversion = (this.pendingConversion = {});
        const html = await htmlPromise;
        if (!html || this.isDestroyed || this.pendingConversion !== conversion) {
            return;
        }
        this.pendingConversion = null;
        restoreSavepoint();
        this.trigger("on_will_paste_handlers", this.dependencies.selection.getEditableSelection());
        const fragment = parseHTML(this.document, html);
        this.dependencies.sanitize.sanitize(fragment);
        // Clean up the invisible text nodes.
        for (const node of descendants(fragment)) {
            if (isTextNode(node) && !isVisibleTextNode(node)) {
                node.remove();
            }
        }
        this.dependencies.dom.insert(fragment);
        this.dependencies.history.commit();
    }

    cancelConversion() {
        this.pendingConversion = null;
    }

    closeMarkdownPowerbox() {
        if (this.isMarkdownPowerboxOpen) {
            this.dependencies.powerbox.closePowerbox();
        }
    }
}
