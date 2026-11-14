import { LANGUAGES } from "@html_editor/others/embedded_components/backend/syntax_highlighting/code_toolbar";
import { newlinesToLineBreaks } from "@html_editor/others/embedded_components/core/syntax_highlighting/syntax_highlighting_utils";
import { Plugin } from "@html_editor/plugin";
import { fillEmpty } from "@html_editor/utils/dom";
import { isTextNode, isVisibleTextNode } from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { isMarkdown } from "./markdown_utils";

/**
 * Markdown support:
 * - When pasting Markdown, open the powerbox to let the user choose between
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
        paste_text_overrides: withSequence(5, this.rememberMarkdown.bind(this)),
        paste_html_overrides: withSequence(5, this.rememberMarkdownFromHtml.bind(this)),
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
    rememberMarkdown(selection, text) {
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
    rememberMarkdownFromHtml(selection, clipboardElem, sanitizedFragment, clipboardData) {
        if (!clipboardElem.querySelector(":not(p, div, br)")) {
            this.rememberMarkdown(selection, clipboardData.getData("text/plain"));
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
        const htmlPromise = rpc("/html_editor/markdown_to_html", { text }).catch(() => null);
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
     * is then kept. The converted HTML is standard HTML, so it is adapted to
     * the editor's format before being inserted (see `adaptConvertedHtml`).
     *
     * @param {Promise<string | null>} htmlPromise
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
        this.adaptConvertedHtml(fragment);
        this.dependencies.dom.insert(fragment);
        this.dependencies.history.commit();
    }

    /**
     * Adapt the standard HTML of the conversion to the editor's format:
     * - Code blocks keep their language if it is supported, and their lines
     *   are separated by line breaks.
     * - Inline code gets the class of the editor's inline code.
     * - List items starting with a checkbox become checklist items, and empty
     *   list items are filled.
     * - Tables get the classes of the editor's tables.
     *
     * This is not done in the plugins of these elements because it is specific
     * to the HTML of the Markdown conversion. This plugin depends on all of
     * them anyway (see `dependencies`), so it is aware of their format.
     *
     * @param {DocumentFragment} fragment
     */
    adaptConvertedHtml(fragment) {
        // Read the language before the code block is replaced by its text.
        for (const code of fragment.querySelectorAll("pre > code[class*='language-']")) {
            const language = [...code.classList]
                .find((className) => className.startsWith("language-"))
                ?.slice("language-".length)
                .toLowerCase();
            if (Object.hasOwn(LANGUAGES, language)) {
                code.parentElement.dataset.languageId = language;
            }
        }
        for (const code of fragment.querySelectorAll("code:not(.o_inline_code)")) {
            if (!closestElement(code, "pre")) {
                code.classList.add("o_inline_code");
            }
        }
        for (const checkbox of fragment.querySelectorAll(
            "li > input[type='checkbox']:first-child, li > p:first-child > input[type='checkbox']:first-child"
        )) {
            const li = closestElement(checkbox, "li");
            if (li.parentElement.nodeName === "UL") {
                li.parentElement.classList.add("o_checklist");
                li.classList.toggle("o_checked", checkbox.hasAttribute("checked"));
            }
            if (checkbox.nextSibling?.nodeType === Node.TEXT_NODE) {
                checkbox.nextSibling.textContent = checkbox.nextSibling.textContent.trimStart();
            }
            checkbox.remove();
        }
        for (const li of fragment.querySelectorAll("li:empty")) {
            fillEmpty(li);
        }
        for (const code of fragment.querySelectorAll("pre > code:only-child")) {
            const pre = code.parentElement;
            pre.textContent = code.textContent.replace(/\n$/, "");
            newlinesToLineBreaks(pre);
        }
        for (const table of fragment.querySelectorAll("table")) {
            table.classList.add("table", "table-bordered", "o_table");
        }
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
