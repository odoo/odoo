import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { unformat } from "./format";
import {
    DEFAULT_LANGUAGE_ID,
    EmbeddedSyntaxHighlightingComponent,
} from "@html_editor/others/embedded_components/backend/syntax_highlighting/syntax_highlighting";
import { expect } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { toExplicitString } from "@web/../lib/hoot/hoot_utils";

/** @typedef {import("@html_editor/plugin").Editor} Editor */
/**
 * @typedef {Object} HighlightedContent
 * @property {string} value
 * @property {string} [language]
 * @property {number | [number, number]} [textareaRange = null] if defined, the
 *                                       focus will be set in the textarea and
 *                                       its selection will be tested
 * @property {boolean} [wrapped = true] if true, the value will be wrapped
 *                                      inside a syntax highlighting block
 */
/**
 * @typedef {Object} FocusedTextarea
 * @property {HTMLTextAreaElement} el
 * @property {string} value
 * @property {number | [number, number]} range
 */

/**
 * Simulate Prism's `highlight` function by wrapping the given `html` string
 * inside a `<span>` element matching with the given `languageId` as `id`
 * attribute.
 * If `ejectBr` is true, take any trailing `<br>` in `html` and insert it after
 * the `<span>` element instead.
 *
 * @param {string} html
 * @param {string} [languageId = DEFAULT_LANGUAGE_ID]
 * @param {boolean} [ejectBr = false]
 * @returns {string}
 */
const highlight = (html, languageId = DEFAULT_LANGUAGE_ID, ejectBr = false) =>
    `<span id="${languageId}">${ejectBr ? html.replace(/((<br>)*)$/, "") : html}</span>${
        ejectBr ? html.match(/(?:<br>)+$/)?.[0] || "" : ""
    }`;

/**
 * Patch the function that loads the Prism library so it doesn't crash when
 * testing and so that its `highlight` function simply wraps the HTML using
 * `highlight`.
 *
 * @see highlight
 */
export const patchPrism = () => {
    patchWithCleanup(EmbeddedSyntaxHighlightingComponent.prototype, {
        async loadPrism() {
            window.Prism = {
                highlight: (html, l, languageId = DEFAULT_LANGUAGE_ID) =>
                    highlight(html, languageId),
                languages: {},
            };
        },
    });
};

/**
 * Test that the document selection is targeting the given `<textarea>` element,
 * that the focus is in it, that is value is the given value, and that its range
 * is the given range.
 *
 * @param {Editor} editor
 * @param {FocusedTextarea} focusedTextarea
 * @param {string} [message]
 */
export const testTextareaRange = (editor, { el, value, range }, message) => {
    range = Array.isArray(range) ? range : [range];
    const start = range[0];
    const end = range.length > 1 ? range[1] : start;
    const { anchorNode, anchorOffset, focusNode, focusOffset } = editor.document.getSelection();
    expect({
        activeElement: editor.document.activeElement,
        anchorTarget: anchorNode.childNodes[anchorOffset],
        focusTarget: focusNode.childNodes[focusOffset],
        textareaValue: el.value,
        textareaRange: [el.selectionStart, el.selectionEnd],
    }).toEqual(
        {
            activeElement: el,
            anchorTarget: el,
            focusTarget: el,
            textareaValue: value,
            textareaRange: [start, end],
        },
        { message: `Selection should be correct in the textarea${message ? ":\n" + message : ""}` }
    );
};

/**
 * Clean the given content to facilitate testing and parse the expected result
 * given as a `HighlightedContent` object (or an array thereof), then compare
 * the two values. If a `textareaRange` key is passed in some of the expected
 * content, test the range and focus in its `<textarea>` element.
 *
 * @param {string} content
 * @param {HighlightedContent | HighlightedContent[]} expected
 * @param {string} phase
 * @param {Editor} editor
 */
export const compareHighlightedContent = async (content, expected, phase, editor) => {
    const cleanedContent = content
        // Ignore embedded props
        .replaceAll(/data-embedded-props='([^']|\n)*' /g, "")
        // Ignore dataset order
        .replaceAll(
            /data-language-id="([^"]+)" data-syntax-highlighting-value="(([^"]|\n)+)"/g,
            `data-syntax-highlighting-value="$2" data-language-id="$1"`
        );
    const message = `(testEditor) ${toExplicitString(
        phase
    )} is strictly equal to "${toExplicitString(expected)}"`;
    await animationFrame();
    // See if `highlightedPre` included textarea range data. If so, parse it,
    // test it, and remove it.
    const strings = expected.split("<textarea");
    strings.shift();
    const textareaIndex = strings.findIndex((str) => str.startsWith("~~~"));
    if (textareaIndex !== -1) {
        const el = editor.editable.querySelectorAll("textarea")[textareaIndex];
        const [range, value] = strings[textareaIndex].match(/~~~([^~]+)~~~/)[1].split("°°°");
        const parsedRange = range.split(",").map((v) => +v.replace(/[[\]]/g, "").trim());
        testTextareaRange(editor, { el, range: parsedRange, value }, message);
        expected = expected.replace(/<textarea~~~[^~]+~~~/g, "<textarea");
    }
    // Now test the content.
    expect(cleanedContent).toBe(expected, { message });
};

export const highlightedPre = ({
    value,
    language = DEFAULT_LANGUAGE_ID,
    textareaRange = null,
    preHtml = value.replaceAll("\n", "<br>"),
}) =>
    unformat(
        `<div data-embedded="syntaxHighlighting" data-oe-protected="true" contenteditable="false"
            class="o_syntax_highlighting"
            data-syntax-highlighting-value="${value}" data-language-id="${language.toLowerCase()}">
            <pre>//PRE//</pre>${textareaRange === null ? "" : "[]"}
            <textarea //TEXTAREA// class="o_prism_source" contenteditable="true"></textarea>
        </div>`
    )
        // Do not trim spaces within the PRE and in the textarea data:
        .replace("//PRE//", highlight(preHtml || "<br>", language, true))
        .replace(
            " //TEXTAREA// ",
            textareaRange ? "~~~" + textareaRange + "°°°" + value + "~~~ " : " "
        );
