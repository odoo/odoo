import { advanceTime, animationFrame, describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import {
    bold,
    deleteBackward,
    deleteForward,
    insertLineBreak,
    insertText,
    keydownShiftTab,
    keydownTab,
    splitBlock,
} from "./_helpers/user_actions";

/**
 * Inline SVGs in the edited content.
 *
 * An inline SVG is edited as a whole, except for the text of its `<text>`
 * elements. Tests marked FIXME show a behavior that is considered wrong.
 *
 * Note: inline SVG elements are in the SVG namespace, so their nodeName is
 * lowercase ("svg", "circle", "text", ...).
 */

const SHAPE = `<svg width="10" height="10"><circle cx="5" cy="5" r="5"></circle></svg>`;
const SHAPE_WS = `<svg width="10" height="10">\n<circle cx="5" cy="5" r="5"></circle>\n</svg>`;
const SHAPE_CEF = `<svg width="10" height="10" contenteditable="false"><circle cx="5" cy="5" r="5"></circle></svg>`;
const textSvg = (inner) => `<svg width="40" height="20"><text x="0" y="15">${inner}</text></svg>`;

describe("SVG with shapes only", () => {
    describe("load", () => {
        test("should keep an inline SVG untouched", async () => {
            await testEditor({
                contentBefore: `<p>ab${SHAPE}cd[]</p>`,
                contentAfter: `<p>ab${SHAPE}cd[]</p>`,
            });
        });

        test("should keep a paragraph containing only an SVG untouched", async () => {
            await testEditor({
                contentBefore: `<p>ab[]</p><p>${SHAPE}</p>`,
                contentAfter: `<p>ab[]</p><p>${SHAPE}</p>`,
            });
        });
    });

    describe("deleteBackward", () => {
        test("should remove the SVG before the cursor", async () => {
            await testEditor({
                contentBefore: `<p>ab${SHAPE}[]cd</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });

        test("should remove the SVG with whitespace nodes before the cursor", async () => {
            await testEditor({
                contentBefore: `<p>ab${SHAPE_WS}[]cd</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });

        test("should remove the SVG at the end of a paragraph", async () => {
            await testEditor({
                contentBefore: `<p>ab${SHAPE}[]</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>ab[]</p>`,
            });
        });

        test("should remove the SVG alone in its paragraph", async () => {
            await testEditor({
                contentBefore: `<p>${SHAPE}[]</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>[]<br></p>`,
            });
        });

        test("should merge a paragraph into a previous one containing only an SVG", async () => {
            await testEditor({
                contentBefore: `<p>${SHAPE}</p><p>[]cd</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>${SHAPE}[]cd</p>`,
            });
        });

        test("should remove a selection containing an SVG", async () => {
            await testEditor({
                contentBefore: `<p>a[b${SHAPE}c]d</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>a[]d</p>`,
            });
        });
    });

    describe("deleteForward", () => {
        test("should remove the SVG after the cursor", async () => {
            await testEditor({
                contentBefore: `<p>ab[]${SHAPE}cd</p>`,
                stepFunction: deleteForward,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });

        test("should merge a next paragraph containing only an SVG", async () => {
            await testEditor({
                contentBefore: `<p>ab[]</p><p>${SHAPE}</p>`,
                stepFunction: deleteForward,
                contentAfter: `<p>ab[]${SHAPE}</p>`,
            });
        });
    });

    describe("splitBlock", () => {
        test("should split after the SVG without altering it", async () => {
            await testEditor({
                contentBefore: `<p>ab${SHAPE}[]cd</p>`,
                stepFunction: splitBlock,
                contentAfter: `<p>ab${SHAPE}</p><p>[]cd</p>`,
            });
        });
    });

    describe("cursor in a whitespace node of the SVG", () => {
        test("FIXME: should not insert text inside the SVG", async () => {
            await testEditor({
                contentBefore: `<p>ab<svg width="10" height="10">[]\n<circle cx="5" cy="5" r="5"></circle>\n</svg>cd</p>`,
                stepFunction: (editor) => insertText(editor, "Z"),
                contentAfter: `<p>ab<svg width="10" height="10">Z[]\n<circle cx="5" cy="5" r="5"></circle>\n</svg>cd</p>`,
            });
        });
    });
});

describe("SVG with text", () => {
    describe("deleteBackward", () => {
        test("should remove the character before the cursor in the SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("xy[]")}cd</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>ab${textSvg("x[]")}cd</p>`,
            });
        });

        test("should remove the last character of the SVG text, keeping a FEFF", async () => {
            // Without a text node, the browser would insert typed text after
            // the SVG.
            await testEditor({
                contentBefore: `<p>ab${textSvg("x[]")}cd</p>`,
                stepFunction: deleteBackward,
                contentAfterEdit: `<p>ab${textSvg("\ufeff[]")}cd</p>`,
                contentAfter: `<p>ab${textSvg("[]")}cd</p>`,
            });
        });

        test("should type in an emptied SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("x[]")}cd</p>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "Z");
                },
                contentAfter: `<p>ab${textSvg("Z[]")}cd</p>`,
            });
        });

        test("should do nothing at the start of the SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("[]xy")}cd</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>ab${textSvg("[]xy")}cd</p>`,
            });
        });

        test("should remove the SVG before the cursor", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("xy")}[]cd</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });

        test("should remove a selection containing an SVG", async () => {
            await testEditor({
                contentBefore: `<p>a[b${textSvg("xy")}c]d</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>a[]d</p>`,
            });
        });
    });

    describe("deleteForward", () => {
        test("should remove the character after the cursor in the SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("x[]y")}cd</p>`,
                stepFunction: deleteForward,
                contentAfter: `<p>ab${textSvg("x[]")}cd</p>`,
            });
        });

        test("should do nothing at the end of the SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("xy[]")}cd</p>`,
                stepFunction: deleteForward,
                contentAfter: `<p>ab${textSvg("xy[]")}cd</p>`,
            });
        });
    });

    describe("insertText", () => {
        test("should insert text in the SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("x[]y")}cd</p>`,
                stepFunction: (editor) => insertText(editor, "Z"),
                contentAfter: `<p>ab${textSvg("xZ[]y")}cd</p>`,
            });
        });

        test("should replace the selected SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("[xy]")}cd</p>`,
                stepFunction: (editor) => insertText(editor, "Z"),
                contentAfter: `<p>ab${textSvg("Z[]")}cd</p>`,
            });
        });
    });

    describe("splitBlock", () => {
        test("should do nothing in the SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("x[]y")}cd</p>`,
                stepFunction: splitBlock,
                contentAfter: `<p>ab${textSvg("x[]y")}cd</p>`,
            });
        });

        test("should move to the next text of the SVG at the end of a text", async () => {
            await testEditor({
                contentBefore: `<p>ab<svg><text>x[]</text><circle r="5"></circle><text>y</text></svg>cd</p>`,
                stepFunction: splitBlock,
                contentAfter: `<p>ab<svg><text>x</text><circle r="5"></circle><text>[]y</text></svg>cd</p>`,
            });
        });

        test("should move to the next text of the SVG at the end of a tspan", async () => {
            await testEditor({
                contentBefore: `<p>ab<svg><text>x<tspan>y[]</tspan></text><text>z</text></svg>cd</p>`,
                stepFunction: splitBlock,
                contentAfter: `<p>ab<svg><text>x<tspan>y</tspan></text><text>[]z</text></svg>cd</p>`,
            });
        });

        test("should move after the SVG at the end of its last text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("xy[]")}cd</p>`,
                stepFunction: splitBlock,
                contentAfter: `<p>ab${textSvg("xy")}[]cd</p>`,
            });
        });

        test("should move after the SVG at the end of its last text, at the end of a paragraph", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("xy[]")}</p>`,
                stepFunction: splitBlock,
                contentAfter: `<p>ab${textSvg("xy")}[]</p>`,
            });
        });
    });

    describe("Tab", () => {
        const threeTexts = (a, b, c) =>
            `<svg><text>${a}</text><circle r="5"></circle><text>${b}</text><text>${c}</text></svg>`;

        test("should select the next text of the SVG", async () => {
            await testEditor({
                contentBefore: `<p>ab${threeTexts("x[]y", "z", "w")}cd</p>`,
                stepFunction: keydownTab,
                contentAfter: `<p>ab${threeTexts("xy", "[z]", "w")}cd</p>`,
            });
        });

        test("should replace the text selected with Tab when typing", async () => {
            // As elsewhere in the editor, the typed text keeps the formatting
            // of the end of the replaced selection (here the <tspan>).
            await testEditor({
                contentBefore: `<p>ab${threeTexts("x[]y", "z<tspan>t</tspan>", "w")}cd</p>`,
                stepFunction: async (editor) => {
                    await keydownTab(editor);
                    await insertText(editor, "N");
                },
                contentAfter: `<p>ab${threeTexts("xy", "<tspan>N[]</tspan>", "w")}cd</p>`,
            });
        });

        test("should move after the SVG from its last text", async () => {
            await testEditor({
                contentBefore: `<p>ab${threeTexts("x", "z", "w[]")}cd</p>`,
                stepFunction: keydownTab,
                contentAfter: `<p>ab${threeTexts("x", "z", "w")}[]cd</p>`,
            });
        });

        test("should select the previous text of the SVG with Shift+Tab", async () => {
            await testEditor({
                contentBefore: `<p>ab${threeTexts("x", "z", "w[]")}cd</p>`,
                stepFunction: keydownShiftTab,
                contentAfter: `<p>ab${threeTexts("x", "[z]", "w")}cd</p>`,
            });
        });

        test("should move before the SVG from its first text with Shift+Tab", async () => {
            await testEditor({
                contentBefore: `<p>ab${threeTexts("x[]", "z", "w")}cd</p>`,
                stepFunction: keydownShiftTab,
                contentAfter: `<p>ab[]${threeTexts("x", "z", "w")}cd</p>`,
            });
        });
    });

    describe("insertLineBreak", () => {
        test("should do nothing in the SVG text", async () => {
            await testEditor({
                contentBefore: `<p>ab${textSvg("x[]y")}cd</p>`,
                stepFunction: insertLineBreak,
                contentAfter: `<p>ab${textSvg("x[]y")}cd</p>`,
            });
        });
    });
});

describe("SVG text and HTML features", () => {
    test("should add a FEFF in an empty SVG text", async () => {
        await testEditor({
            contentBefore: `<p>ab[]${textSvg("")}cd</p>`,
            contentAfterEdit: `<p>ab[]${textSvg("\ufeff")}cd</p>`,
            contentAfter: `<p>ab[]${textSvg("")}cd</p>`,
        });
    });

    test("should not format the SVG text", async () => {
        await testEditor({
            contentBefore: `<p>ab${textSvg("[xy]")}cd</p>`,
            stepFunction: bold,
            contentAfter: `<p>ab${textSvg("[xy]")}cd</p>`,
        });
    });

    test("should not open the toolbar on a selection in the SVG text", async () => {
        await setupEditor(`<p>ab${textSvg("[xy]")}cd</p>`);
        await animationFrame();
        await advanceTime(500);
        expect(".o-we-toolbar").toHaveCount(0);
    });

    test("should not open the powerbox in the SVG text", async () => {
        const { editor } = await setupEditor(`<p>ab${textSvg("x[]")}cd</p>`);
        await insertText(editor, "/");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);
    });
});

describe("SVG flagged contenteditable=false", () => {
    test("should remove the SVG at the end of a paragraph", async () => {
        await testEditor({
            contentBefore: `<p>ab${SHAPE_CEF}[]</p>`,
            stepFunction: deleteBackward,
            contentAfter: `<p>ab[]</p>`,
        });
    });

    test("should remove the SVG alone in its paragraph", async () => {
        await testEditor({
            contentBefore: `<p>${SHAPE_CEF}[]</p>`,
            stepFunction: deleteBackward,
            contentAfter: `<p>[]<br></p>`,
        });
    });

    test("should merge a next paragraph containing only an SVG", async () => {
        await testEditor({
            contentBefore: `<p>ab[]</p><p>${SHAPE_CEF}</p>`,
            stepFunction: deleteForward,
            contentAfter: `<p>ab[]${SHAPE_CEF}</p>`,
        });
    });

    test("should split after the SVG without altering it", async () => {
        await testEditor({
            contentBefore: `<p>ab${SHAPE_CEF}[]cd</p>`,
            stepFunction: splitBlock,
            contentAfter: `<p>ab${SHAPE_CEF}</p><p>[]cd</p>`,
        });
    });

    test("should remove the SVG before the cursor", async () => {
        await testEditor({
            contentBefore: `<p>ab${SHAPE_CEF}[]cd</p>`,
            stepFunction: deleteBackward,
            contentAfter: `<p>ab[]cd</p>`,
        });
    });
});
