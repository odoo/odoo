import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { unformat } from "./format";
import { SyntaxHighlightingPlugin } from "@html_editor/main/syntax_highlighting_plugin";

const DEFAULT_LANGUAGE_ID = "plaintext";
const WITH_LANGUAGE_ID = (html, languageId = DEFAULT_LANGUAGE_ID) =>
    `<span id="${languageId}">${html}</span>`;
export const getPreStyle = (editor) =>
    editor.document.defaultView.getComputedStyle(editor.editable.querySelector("pre"));
export const SYNTAX_HIGHLIGHTING_WRAPPER = (
    content,
    {
        language = DEFAULT_LANGUAGE_ID,
        highlight = true,
        focused = false,
        preStyle = {
            font: '13px / 19.5px SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            margin: "0px 0px 16px",
            padding: "8px 16px",
        },
    } = {}
) =>
    unformat(`
        <div class="o_syntax_highlighting" data-language-id="${language}"
            style='font: ${preStyle.font};' data-oe-protected="true" contenteditable="false">
            <pre data-oe-protected="false" contenteditable="true">`) +
    (highlight ? WITH_LANGUAGE_ID(content, language) : content) + // Do not trim spaces within the PRE.
    unformat(`</pre>${focused ? "[]" : ""}
            <textarea class="o_prism_source" contenteditable="true"
            style="padding: ${preStyle.padding}; margin: ${preStyle.margin};"></textarea>
            </div>
    `);
export const patchPrism = () => {
    patchWithCleanup(SyntaxHighlightingPlugin.prototype, {
        async loadPrism() {
            window.Prism = {
                highlight: (html, l, languageId = DEFAULT_LANGUAGE_ID) =>
                    WITH_LANGUAGE_ID(html, languageId),
                languages: {},
            };
        },
    });
};
