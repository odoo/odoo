import { expect } from "@odoo/hoot";
import { testEditor } from "./editor";

export const TAB_WIDTH = 40;

let charWidths = undefined;
let indentWidths = undefined;

function setWidths() {
    if (charWidths && indentWidths) {
        // charWidths and indentWidths are global variables that need to be set
        // only once.
        return;
    }
    charWidths = {};
    indentWidths = {};

    const rootDiv = document.createElement("div");
    rootDiv.classList.add("odoo-editor-editable");
    rootDiv.contentEditable = true;
    document.body.append(rootDiv);

    const referenceBlock = document.createElement("p");
    rootDiv.append(referenceBlock);
    const referenceLeft = referenceBlock.getBoundingClientRect().left;

    const range = new Range();
    const tags = ["p", "h1", "blockquote", "li"];
    const chars = ["a", "b", "c", "d", "e", "f"];
    for (const tag of tags) {
        let element;
        if (tag === "li") {
            const ul = document.createElement("ul");
            element = document.createElement("li");
            ul.append(element);
            rootDiv.append(ul);
        } else {
            element = document.createElement(tag);
            rootDiv.append(element);
        }

        // Calculate the base indentation (result of margin, padding and border)
        // for the given block.
        element.textContent = "|";
        range.selectNodeContents(element);
        const indentWidth = range.getBoundingClientRect().left - referenceLeft;
        indentWidths[tag] = indentWidth;

        // Calculate the width of each char in the given block.
        charWidths[tag] = {};
        for (const char of chars) {
            element.textContent = char;
            range.selectNodeContents(element);
            const width = range.getBoundingClientRect().width;
            charWidths[tag][char] = width;
        }
    }
    rootDiv.remove();
}

export function getCharWidth(tag, char) {
    if (!charWidths) {
        setWidths();
    }
    return charWidths[tag][char];
}

export function getIndentWidth(tag) {
    if (!indentWidths) {
        setWidths();
    }
    return indentWidths[tag];
}

export function oeTab(size, contenteditable = true) {
    return (
        `<span class="oe-tabs"` +
        (contenteditable ? "" : ' contenteditable="false"') +
        (size ? ` style="width: ${Number(size.toFixed(1))}px;"` : "") +
        `>\u0009</span>\u200B`
    );
}

/**
 * Extracts the style.width values from the given content and replaces them with a placeholder.
 * @param {string} content
 * @returns {Object} - { text: string, widths: number[] }
 */
function extractWidth(content) {
    const regex = /width: ([\d.]+)px;/g;
    const widths = [];
    const text = content.replaceAll(regex, (_, w) => {
        widths.push(parseFloat(w));
        return `width: _px;`;
    });
    return { text, widths };
}

/**
 * Compares the two contents with hoot expect.
 * Style.width values are allowed to differ by a margin of tolerance.
 *
 * @param {string} contentEl
 * @param {string} contentSpec
 * @param {"contentAfterEdit"|"contentAfter"} mode
 */
function compare(contentEl, contentSpec, mode) {
    const maxDiff = 0.5;
    const { text: receivedContent, widths: receivedWidths } = extractWidth(contentEl);
    const { text: expectedContent, widths: expectedWidths } = extractWidth(contentSpec);

    expect(receivedContent).toBe(expectedContent, {
        message: `(testEditor) ${mode} should be strictly equal to ${expectedContent}`,
    });

    const diffs = expectedWidths.map((width, i) => Math.abs(width - receivedWidths[i]));
    expect(Math.max(...diffs)).toBeLessThan(maxDiff, {
        message:
            `(testEditor) (${mode}) tab widths differ by less than ${maxDiff} pixel\n` +
            diffs
                .map(
                    (diff, i) =>
                        `tab[${i}] ` +
                        `received: ${receivedWidths[i]}, ` +
                        `expected: ${expectedWidths[i]}, ` +
                        `diff: ${diff.toFixed(1)}`
                )
                .join("\n"),
    });
}

export function testTabulation(params) {
    return testEditor({ ...params, compareFunction: compare });
}
