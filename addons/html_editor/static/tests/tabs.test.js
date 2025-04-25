import { describe, test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";
import { TAB_WIDTH, getCharWidth, getIndentWidth, oeTab, testTabulation } from "./_helpers/tabs";
import {
    deleteBackward,
    deleteForward,
    insertText,
    keydownShiftTab,
    keydownTab,
} from "./_helpers/user_actions";

describe("insert tabulation", () => {
    test("should insert a tab character", async () => {
        const expectedTabWidth = TAB_WIDTH - getCharWidth("p", "a");
        await testTabulation({
            contentBefore: `<p>a[]b</p>`,
            stepFunction: keydownTab,
            contentAfterEdit: `<p>a${oeTab(expectedTabWidth, false)}[]b</p>`,
            contentAfter: `<p>a${oeTab(expectedTabWidth)}[]b</p>`,
        });
    });

    test("should keep selection and insert a tab character at the beginning of the paragraph", async () => {
        await testTabulation({
            contentBefore: `<p>a[xxx]b</p>`,
            stepFunction: keydownTab,
            contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}a[xxx]b</p>`,
            contentAfter: `<p>${oeTab(TAB_WIDTH)}a[xxx]b</p>`,
        });
    });

    test("should insert two tab characters", async () => {
        const expectedTabWidth = TAB_WIDTH - getCharWidth("p", "a");
        await testTabulation({
            contentBefore: `<p>a[]b</p>`,
            stepFunction: async (editor) => {
                await keydownTab(editor);
                await keydownTab(editor);
            },
            contentAfterEdit: `<p>a${oeTab(expectedTabWidth, false)}${oeTab(
                TAB_WIDTH,
                false
            )}[]b</p>`,
            contentAfter: `<p>a${oeTab(expectedTabWidth)}${oeTab(TAB_WIDTH)}[]b</p>`,
        });
    });

    test("should insert two tab characters with one char between them", async () => {
        const expectedTabWidth = TAB_WIDTH - getCharWidth("p", "a");
        await testTabulation({
            contentBefore: `<p>a[]b</p>`,
            stepFunction: async (editor) => {
                await keydownTab(editor);
                await insertText(editor, "a");
                await keydownTab(editor);
            },
            contentAfterEdit: `<p>a${oeTab(expectedTabWidth, false)}a${oeTab(
                expectedTabWidth,
                false
            )}[]b</p>`,
            contentAfter: `<p>a${oeTab(expectedTabWidth)}a${oeTab(expectedTabWidth)}[]b</p>`,
        });
    });

    test("tab should not be colored when inserting tab at the beginning of a text having background color", async () => {
        await testTabulation({
            contentBefore: `<p><font style="background-color: rgb(255,255,0);">[]ab</font></p>`,
            stepFunction: keydownTab,
            contentAfterEdit: `<p>${oeTab(
                TAB_WIDTH,
                false
            )}<font style="background-color: rgb(255,255,0);">[]ab</font></p>`,
            contentAfter: `<p>${oeTab(
                TAB_WIDTH
            )}<font style="background-color: rgb(255,255,0);">[]ab</font></p>`,
        });
    });

    test("tab should not be colored when inserting tab at the beginning of a text having background color (2)", async () => {
        await testTabulation({
            contentBefore: `<p><font style="background-color: rgb(255,255,0);">\u200B[]</font></p>`,
            stepFunction: keydownTab,
            contentAfterEdit: `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">${oeTab(
                TAB_WIDTH,
                false
            )}<font style="background-color: rgb(255,255,0);">\u200B[]</font></p>`,
            contentAfter: `<p>${oeTab(
                TAB_WIDTH
            )}<font style="background-color: rgb(255,255,0);">\u200B[]</font></p>`,
        });
    });

    test("tabs should not be colored when inserting multiple tabs at the beginning of a text having background color", async () => {
        await testTabulation({
            contentBefore: `<p><font style="background-color: rgb(255,255,0);">[]ab</font></p>`,
            stepFunction: async (editor) => {
                await keydownTab(editor);
                await keydownTab(editor);
            },
            contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}${oeTab(
                TAB_WIDTH,
                false
            )}<font style="background-color: rgb(255,255,0);">[]ab</font></p>`,
            contentAfter: `<p>${oeTab(TAB_WIDTH)}${oeTab(
                TAB_WIDTH
            )}<font style="background-color: rgb(255,255,0);">[]ab</font></p>`,
        });
    });

    test("tab should be colored when inserting a tab in the middle of text having background color", async () => {
        const expectedTabWidth = TAB_WIDTH - getCharWidth("p", "a");
        await testTabulation({
            contentBefore: `<p><font style="background-color: rgb(255,255,0);">a[]b</font></p>`,
            stepFunction: keydownTab,
            contentAfterEdit: `<p><font style="background-color: rgb(255,255,0);">a${oeTab(
                expectedTabWidth,
                false
            )}[]b</font></p>`,
            contentAfter: `<p><font style="background-color: rgb(255,255,0);">a${oeTab(
                expectedTabWidth
            )}[]b</font></p>`,
        });
    });

    test("tab should be colored when inserting a tab in the middle of text having background color (2)", async () => {
        const expectedTabWidth = TAB_WIDTH - (getCharWidth("p", "a") + getCharWidth("p", "b"));
        await testTabulation({
            contentBefore: `<p><font style="background-color: rgb(255,255,0);">ab<strong>[]cd</strong></font></p>`,
            stepFunction: keydownTab,
            contentAfterEdit: `<p><font style="background-color: rgb(255,255,0);">ab${oeTab(
                expectedTabWidth,
                false
            )}<strong>[]cd</strong></font></p>`,
            contentAfter: `<p><font style="background-color: rgb(255,255,0);">ab${oeTab(
                expectedTabWidth
            )}<strong>[]cd</strong></font></p>`,
        });
    });

    test("tab should be colored when inserting a tab in the end of text having background color", async () => {
        const expectedTabWidth = TAB_WIDTH - (getCharWidth("p", "a") + getCharWidth("p", "b"));
        await testTabulation({
            contentBefore: `<p><font style="background-color: rgb(255,255,0);">ab[]</font></p>`,
            stepFunction: keydownTab,
            contentAfterEdit: `<p><font style="background-color: rgb(255,255,0);">ab${oeTab(
                expectedTabWidth,
                false
            )}[]</font></p>`,
            contentAfter: `<p><font style="background-color: rgb(255,255,0);">ab${oeTab(
                expectedTabWidth
            )}[]</font></p>`,
        });
    });

    test("should insert tab characters at the beginning of two separate paragraphs", async () => {
        await testTabulation({
            contentBefore: `<p>a[b</p>` + `<p>c]d</p>`,
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` + `<p>${oeTab(TAB_WIDTH, false)}c]d</p>`,
            contentAfter: `<p>${oeTab(TAB_WIDTH)}a[b</p>` + `<p>${oeTab(TAB_WIDTH)}c]d</p>`,
        });
    });

    test("should insert tab characters at the beginning of two separate indented paragraphs", async () => {
        await testTabulation({
            contentBefore: `<p>${oeTab()}a[b</p>` + `<p>${oeTab()}c]d</p>`,
            // @todo: add contentBeforeEdit in some test cases to test the addition
            // of the contenteditable="false" attribute by setup.
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[b</p>` +
                `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}c]d</p>`,
            contentAfter:
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[b</p>` +
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}c]d</p>`,
        });
    });

    test("should insert tab characters at the beginning of two separate paragraphs (one indented, the other not)", async () => {
        await testTabulation({
            contentBefore: `<p>${oeTab()}a[b</p>` + `<p>c]d</p>`,
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[b</p>` +
                `<p>${oeTab(TAB_WIDTH, false)}c]d</p>`,
            contentAfter:
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[b</p>` +
                `<p>${oeTab(TAB_WIDTH)}c]d</p>`,
        });
        await testTabulation({
            contentBefore: `<p>a[b</p>` + `<p>${oeTab()}c]d</p>`,
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}c]d</p>`,
            contentAfter:
                `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}c]d</p>`,
        });
    });

    test("should insert tab characters at the beginning of two separate paragraphs with tabs in them", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        const tabAfterB = TAB_WIDTH - getCharWidth("p", "b");
        const tabAfterC = TAB_WIDTH - getCharWidth("p", "c");
        const tabAfterD = TAB_WIDTH - getCharWidth("p", "d");

        await testTabulation({
            contentBefore:
                `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` + `<p>c${oeTab()}]d${oeTab()}</p>`,
            stepFunction: keydownTab,
            contentAfter:
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[${oeTab(tabAfterA)}b${oeTab(
                    tabAfterB
                )}</p>` + `<p>${oeTab(TAB_WIDTH)}c${oeTab(tabAfterC)}]d${oeTab(tabAfterD)}</p>`,
        });
    });

    test("should insert tab characters at the beginning of three separate blocks", async () => {
        const tabInBlockquote = TAB_WIDTH - getIndentWidth("blockquote");

        await testTabulation({
            contentBefore:
                `<p>xxx</p>` +
                `<p>a[b</p>` +
                `<h1>cd</h1>` +
                `<blockquote>e]f</blockquote>` +
                `<h4>zzz</h4>`,
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>xxx</p>` +
                `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                `<h1>${oeTab(TAB_WIDTH, false)}cd</h1>` +
                `<blockquote>${oeTab(tabInBlockquote, false)}e]f</blockquote>` +
                `<h4>zzz</h4>`,
            contentAfter:
                `<p>xxx</p>` +
                `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                `<h1>${oeTab(TAB_WIDTH)}cd</h1>` +
                `<blockquote>${oeTab(tabInBlockquote)}e]f</blockquote>` +
                `<h4>zzz</h4>`,
        });
    });

    test("should insert tab characters at the beginning of three separate indented blocks", async () => {
        const tabInBlockquote = TAB_WIDTH - getIndentWidth("blockquote");

        await testTabulation({
            contentBefore:
                `<p>${oeTab()}xxx</p>` +
                `<p>${oeTab()}a[b</p>` +
                `<h1>${oeTab()}cd</h1>` +
                `<blockquote>${oeTab()}e]f</blockquote>` +
                `<h4>${oeTab()}zzz</h4>`,
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>${oeTab(TAB_WIDTH, false)}xxx</p>` +
                `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[b</p>` +
                `<h1>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}cd</h1>` +
                `<blockquote>${oeTab(tabInBlockquote, false)}${oeTab(
                    TAB_WIDTH,
                    false
                )}e]f</blockquote>` +
                `<h4>${oeTab(TAB_WIDTH, false)}zzz</h4>`,
            contentAfter:
                `<p>${oeTab(TAB_WIDTH)}xxx</p>` +
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[b</p>` +
                `<h1>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}cd</h1>` +
                `<blockquote>${oeTab(tabInBlockquote)}${oeTab(TAB_WIDTH)}e]f</blockquote>` +
                `<h4>${oeTab(TAB_WIDTH)}zzz</h4>`,
        });
    });

    test("should insert tab characters at the beginning of three separate blocks of mixed indentation", async () => {
        const tabInBlockquote = TAB_WIDTH - getIndentWidth("blockquote");

        await testTabulation({
            contentBefore:
                `<p>xxx</p>` +
                `<p>${oeTab()}${oeTab()}a[b</p>` +
                `<h1>${oeTab()}cd</h1>` +
                `<blockquote>e]f</blockquote>` +
                `<h4>zzz</h4>`,
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>xxx</p>` +
                `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}${oeTab(
                    TAB_WIDTH,
                    false
                )}a[b</p>` +
                `<h1>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}cd</h1>` +
                `<blockquote>${oeTab(tabInBlockquote, false)}e]f</blockquote>` +
                `<h4>zzz</h4>`,
            contentAfter:
                `<p>xxx</p>` +
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[b</p>` +
                `<h1>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}cd</h1>` +
                `<blockquote>${oeTab(tabInBlockquote)}e]f</blockquote>` +
                `<h4>zzz</h4>`,
        });
    });

    test("should insert tab characters at the beginning of three separate blocks with tabs in them", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        const tabAfterB = TAB_WIDTH - getCharWidth("p", "b");
        const tabAfterCinH1 = TAB_WIDTH - getCharWidth("h1", "c");
        const tabAfterDinH1 = TAB_WIDTH - getCharWidth("h1", "d");
        const tabInBlockquote = TAB_WIDTH - getIndentWidth("blockquote");
        const tabAfterEinBlockquote = TAB_WIDTH - getCharWidth("blockquote", "e"); // in bloquote, after a tab

        await testTabulation({
            contentBefore:
                `<p>xxx</p>` +
                `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                `<h1>c${oeTab()}d${oeTab()}</h1>` +
                `<blockquote>e${oeTab()}]f</blockquote>` +
                `<h4>zzz</h4>`,
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>xxx</p>` +
                `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[${oeTab(
                    tabAfterA,
                    false
                )}b${oeTab(tabAfterB, false)}</p>` +
                `<h1>${oeTab(TAB_WIDTH, false)}c${oeTab(tabAfterCinH1, false)}d${oeTab(
                    tabAfterDinH1,
                    false
                )}</h1>` +
                `<blockquote>${oeTab(tabInBlockquote, false)}e${oeTab(
                    tabAfterEinBlockquote,
                    false
                )}]f</blockquote>` +
                `<h4>zzz</h4>`,
            contentAfter:
                `<p>xxx</p>` +
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[${oeTab(tabAfterA)}b${oeTab(
                    tabAfterB
                )}</p>` +
                `<h1>${oeTab(TAB_WIDTH)}c${oeTab(tabAfterCinH1)}d${oeTab(tabAfterDinH1)}</h1>` +
                `<blockquote>${oeTab(tabInBlockquote)}e${oeTab(
                    tabAfterEinBlockquote
                )}]f</blockquote>` +
                `<h4>zzz</h4>`,
        });
    });

    test("should insert tab characters in blocks and indent lists", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        const tabAfterB = TAB_WIDTH - getCharWidth("p", "b");
        const tabAfterCinNestedLI =
            TAB_WIDTH - ((2 * getIndentWidth("li") + getCharWidth("li", "c")) % TAB_WIDTH);
        const tabAfterD = TAB_WIDTH - getCharWidth("li", "d"); // in LI, after a tab
        const tabInDoubleNestedList = TAB_WIDTH - ((3 * getIndentWidth("li")) % TAB_WIDTH);
        const tabAfterE = TAB_WIDTH - getCharWidth("li", "e"); // in LI, after a tab
        const tabInBlockquote = TAB_WIDTH - getIndentWidth("blockquote");
        const tabAfterFinBlockquote = TAB_WIDTH - getCharWidth("blockquote", "f"); // in blockquote, after a tab

        // prettier-ignore
        await testTabulation({
            // Obs: cannot use `unformat` for tests with tabs (as it removes the \t chars)
            contentBefore:
                `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                `<ul>` +
                    `<li><p>c${oeTab()}d${oeTab()}</p>` +
                        `<ul>` +
                            `<li>${oeTab()}e${oeTab()}</li>` +
                        `</ul>` +
                    `</li>` +
                `</ul>` +
                `<blockquote>f${oeTab()}]g</blockquote>`,
            stepFunction: keydownTab,
            contentAfterEdit:
                `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[${oeTab(tabAfterA, false)}b${oeTab(tabAfterB,false)}</p>` +
                `<ul>` +
                    `<li class="oe-nested">` +
                        `<ul>` +
                            `<li><p>c${oeTab(tabAfterCinNestedLI, false)}d${oeTab(tabAfterD, false)}</p>` +
                                `<ul>` +
                                    `<li>${oeTab(tabInDoubleNestedList, false)}e${oeTab(tabAfterE, false)}</li>` +
                                `</ul>` +
                            `</li>` +
                        `</ul>` +
                    `</li>` +
                `</ul>` +
                `<blockquote>${oeTab(tabInBlockquote, false)}f${oeTab(tabAfterFinBlockquote, false)}]g</blockquote>`,
            contentAfter:
                `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[${oeTab(tabAfterA)}b${oeTab(tabAfterB)}</p>` +
                `<ul>` +
                    `<li class="oe-nested">` +
                        `<ul>` +
                            `<li><p>c${oeTab(tabAfterCinNestedLI)}d${oeTab(tabAfterD)}</p>` +
                                `<ul>` +
                                    `<li>${oeTab(tabInDoubleNestedList)}e${oeTab(tabAfterE)}</li>` +
                                `</ul>` +
                            `</li>` +
                        `</ul>` +
                    `</li>` +
                `</ul>` +
                `<blockquote>${oeTab(tabInBlockquote)}f${oeTab(tabAfterFinBlockquote)}]g</blockquote>`,
        });
    });
});

describe("delete backward tabulation", () => {
    test("should remove one tab character", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}[]b</p>`,
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfter: `<p>a[]b</p>`,
        });
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}[]${oeTab()}b</p>`,
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfter: `<p>a[]${oeTab(tabAfterA)}b</p>`,
        });
    });

    test("should remove two tab characters", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}${oeTab()}[]b</p>`,
            stepFunction: async (editor) => {
                deleteBackward(editor);
                deleteBackward(editor);
            },
            contentAfter: `<p>a[]b</p>`,
        });
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}${oeTab()}[]${oeTab()}b</p>`,
            stepFunction: async (editor) => {
                deleteBackward(editor);
                deleteBackward(editor);
            },
            contentAfter: `<p>a[]${oeTab(tabAfterA)}b</p>`,
        });
    });

    test("should remove three tab characters", async () => {
        await testEditor({
            contentBefore: `<p>a${oeTab()}${oeTab()}${oeTab()}[]b</p>`,
            stepFunction: async (editor) => {
                deleteBackward(editor);
                deleteBackward(editor);
                deleteBackward(editor);
            },
            contentAfter: `<p>a[]b</p>`,
        });
    });
});

describe("delete forward tabulation", () => {
    test("should remove one tab character", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        await testTabulation({
            contentBefore: `<p>a[]${oeTab(tabAfterA)}b1</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
            },
            contentAfter: `<p>a[]b1</p>`,
        });
        await testTabulation({
            contentBefore: `<p>a${oeTab(tabAfterA)}[]${oeTab()}b2</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
            },
            contentAfter: `<p>a${oeTab(tabAfterA)}[]b2</p>`,
        });
        await testTabulation({
            contentBefore: `<p>a[]${oeTab(tabAfterA)}${oeTab()}b3</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
            },
            contentAfter: `<p>a[]${oeTab(tabAfterA)}b3</p>`,
        });
    });

    test("should remove two tab characters", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        await testEditor({
            contentBefore: `<p>a[]${oeTab(tabAfterA)}${oeTab()}b1</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
                deleteForward(editor);
            },
            contentAfter: `<p>a[]b1</p>`,
        });
        await testEditor({
            contentBefore: `<p>a[]${oeTab(tabAfterA)}${oeTab()}${oeTab()}b2</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
                deleteForward(editor);
            },
            contentAfter: `<p>a[]${oeTab(tabAfterA)}b2</p>`,
        });
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}[]${oeTab()}${oeTab()}b3</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
                deleteForward(editor);
            },
            contentAfter: `<p>a${oeTab(tabAfterA)}[]b3</p>`,
        });
    });

    test("should remove three tab characters", async () => {
        await testEditor({
            contentBefore: `<p>a[]${oeTab()}${oeTab()}${oeTab()}b</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
                deleteForward(editor);
                deleteForward(editor);
            },
            contentAfter: `<p>a[]b</p>`,
        });
    });
});

describe("delete mixed tabulation", () => {
    test("should remove all tab characters", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}[]${oeTab()}b1</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
                deleteBackward(editor);
            },
            contentAfter: `<p>a[]b1</p>`,
        });
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}[]${oeTab()}b2</p>`,
            stepFunction: async (editor) => {
                deleteBackward(editor);
                deleteForward(editor);
            },
            contentAfter: `<p>a[]b2</p>`,
        });
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}${oeTab()}[]${oeTab()}b3</p>`,
            stepFunction: async (editor) => {
                deleteBackward(editor);
                deleteForward(editor);
                deleteBackward(editor);
            },
            contentAfter: `<p>a[]b3</p>`,
        });
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}[]${oeTab()}${oeTab()}b4</p>`,
            stepFunction: async (editor) => {
                deleteForward(editor);
                deleteBackward(editor);
                deleteForward(editor);
            },
            contentAfter: `<p>a[]b4</p>`,
        });
    });
});

describe("remove tabulation with shift+tab", () => {
    test("should not remove a non-leading tab character", async () => {
        function oeTab(size, contenteditable = true) {
            return (
                `<span class="oe-tabs"` +
                (size ? ` style="width: ${size.toFixed(1)}px;"` : "") +
                (contenteditable ? "" : ' contenteditable="false"') +
                `>\u0009</span>\u200B`
            );
        }
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        await testEditor({
            contentBefore: `<p>a${oeTab(tabAfterA)}[]b</p>`,
            stepFunction: keydownShiftTab,
            contentAfterEdit: `<p>a${oeTab(tabAfterA, false)}[]b</p>`,
            contentAfter: `<p>a${oeTab(tabAfterA)}[]b</p>`,
        });
    });

    test("should remove a tab character", async () => {
        await testEditor({
            contentBefore: `<p>${oeTab()}a[]b</p>`,
            stepFunction: keydownShiftTab,
            contentAfter: `<p>a[]b</p>`,
        });
    });

    test("should keep selection and remove a tab character from the beginning of the paragraph", async () => {
        await testEditor({
            contentBefore: `<p>${oeTab()}a[xxx]b</p>`,
            stepFunction: keydownShiftTab,
            contentAfter: `<p>a[xxx]b</p>`,
        });
    });

    test("should remove two tab characters", async () => {
        await testEditor({
            contentBefore: `<p>${oeTab()}${oeTab()}a[]b</p>`,
            stepFunction: async (editor) => {
                await keydownShiftTab(editor);
                await keydownShiftTab(editor);
            },
            contentAfter: `<p>a[]b</p>`,
        });
    });

    test("should remove tab characters from the beginning of two separate paragraphs", async () => {
        await testEditor({
            contentBefore: `<p>${oeTab()}a[b</p>` + `<p>${oeTab()}c]d</p>`,
            stepFunction: keydownShiftTab,
            contentAfter: `<p>a[b</p>` + `<p>c]d</p>`,
        });
    });

    test("should remove tab characters from the beginning of two separate double-indented paragraphs", async () => {
        await testTabulation({
            contentBefore: `<p>${oeTab()}${oeTab()}a[b</p>` + `<p>${oeTab()}${oeTab()}c]d</p>`,
            stepFunction: keydownShiftTab,
            contentAfterEdit:
                `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` + `<p>${oeTab(TAB_WIDTH, false)}c]d</p>`,
            contentAfter: `<p>${oeTab(TAB_WIDTH)}a[b</p>` + `<p>${oeTab(TAB_WIDTH)}c]d</p>`,
        });
    });

    test("should remove tab characters from the beginning of two separate paragraphs of mixed indentations", async () => {
        await testTabulation({
            contentBefore: `<p>${oeTab()}${oeTab()}a[b</p>` + `<p>${oeTab()}c]d</p>`,
            stepFunction: keydownShiftTab,
            contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` + `<p>c]d</p>`,
            contentAfter: `<p>${oeTab(TAB_WIDTH)}a[b</p>` + `<p>c]d</p>`,
        });
        await testTabulation({
            contentBefore: `<p>a[b</p>` + `<p>${oeTab()}c]d</p>`,
            stepFunction: keydownShiftTab,
            contentAfter: `<p>a[b</p>` + `<p>c]d</p>`,
        });
    });

    test("should remove tab characters from the beginning of two separate paragraphs with tabs in them", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        const tabAfterB = TAB_WIDTH - getCharWidth("p", "b");
        const tabAfterC = TAB_WIDTH - getCharWidth("p", "c");
        const tabAfterD = TAB_WIDTH - getCharWidth("p", "d");
        await testTabulation({
            contentBefore:
                `<p>${oeTab(TAB_WIDTH)}a[${oeTab(tabAfterA)}b${oeTab(tabAfterB)}</p>` +
                `<p>c${oeTab(tabAfterC)}]d${oeTab(tabAfterD)}</p>`,
            stepFunction: keydownShiftTab,
            contentAfter:
                `<p>a[${oeTab(tabAfterA)}b${oeTab(tabAfterB)}</p>` +
                `<p>c${oeTab(tabAfterC)}]d${oeTab(tabAfterD)}</p>`,
        });
    });

    test("should remove tab characters from the beginning of three separate blocks", async () => {
        await testEditor({
            contentBefore:
                `<p>xxx</p>` +
                `<p>${oeTab()}a[b</p>` +
                `<h1>${oeTab()}cd</h1>` +
                `<blockquote>${oeTab()}e]f</blockquote>` +
                `<h4>zzz</h4>`,
            stepFunction: keydownShiftTab,
            contentAfter:
                `<p>xxx</p>` +
                `<p>a[b</p>` +
                `<h1>cd</h1>` +
                `<blockquote>e]f</blockquote>` +
                `<h4>zzz</h4>`,
        });
    });

    test("should remove tab characters from the beginning of three separate blocks of mixed indentation", async () => {
        await testTabulation({
            contentBefore:
                `<p>xxx</p>` +
                `<p>${oeTab()}${oeTab()}a[b</p>` +
                `<h1>${oeTab()}cd</h1>` +
                `<blockquote>e]f</blockquote>` +
                `<h4>zzz</h4>`,
            stepFunction: keydownShiftTab,
            contentAfterEdit:
                `<p>xxx</p>` +
                `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                `<h1>cd</h1>` +
                `<blockquote>e]f</blockquote>` +
                `<h4>zzz</h4>`,
            contentAfter:
                `<p>xxx</p>` +
                `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                `<h1>cd</h1>` +
                `<blockquote>e]f</blockquote>` +
                `<h4>zzz</h4>`,
        });
    });

    test("should remove tab characters from the beginning of three separate blocks with tabs in them", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        const tabAfterB = TAB_WIDTH - getCharWidth("p", "b");
        const tabAfterCinH1 = TAB_WIDTH - getCharWidth("h1", "c");
        const tabAfterDinH1 = TAB_WIDTH - getCharWidth("h1", "d");
        const tabAfterEinBlockquote =
            TAB_WIDTH - (getIndentWidth("blockquote") + getCharWidth("blockquote", "e"));

        await testTabulation({
            contentBefore:
                `<p>xxx</p>` +
                `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                `<h1>${oeTab()}c${oeTab()}d${oeTab()}</h1>` +
                `<blockquote>${oeTab()}e${oeTab()}]f</blockquote>` +
                `<h4>zzz</h4>`,
            stepFunction: keydownShiftTab,
            contentAfterEdit:
                `<p>xxx</p>` +
                `<p>a[${oeTab(tabAfterA, false)}b${oeTab(tabAfterB, false)}</p>` +
                `<h1>c${oeTab(tabAfterCinH1, false)}d${oeTab(tabAfterDinH1, false)}</h1>` +
                `<blockquote>e${oeTab(tabAfterEinBlockquote, false)}]f</blockquote>` +
                `<h4>zzz</h4>`,
            contentAfter:
                `<p>xxx</p>` +
                `<p>a[${oeTab(tabAfterA)}b${oeTab(tabAfterB)}</p>` +
                `<h1>c${oeTab(tabAfterCinH1)}d${oeTab(tabAfterDinH1)}</h1>` +
                `<blockquote>e${oeTab(tabAfterEinBlockquote)}]f</blockquote>` +
                `<h4>zzz</h4>`,
        });
    });

    test("should remove tab characters from the beginning of blocks and outdent lists", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        const tabAfterB = TAB_WIDTH - getCharWidth("p", "b");
        const tabAfterCinLI =
            TAB_WIDTH - ((getIndentWidth("li") + getCharWidth("li", "c")) % TAB_WIDTH);
        const tabAfterD = TAB_WIDTH - getCharWidth("li", "d"); // in LI, after a tab
        const tabAfterE = TAB_WIDTH - getCharWidth("li", "e"); // in LI, after a tab
        const tabInNestedList = TAB_WIDTH - ((2 * getIndentWidth("li")) % TAB_WIDTH);
        const tabAfterFinBlockquote =
            TAB_WIDTH - (getIndentWidth("blockquote") + getCharWidth("blockquote", "f"));

        await testTabulation({
            contentBefore:
                `<p>${oeTab()}${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                `<ul>` +
                `<li class="oe-nested"><ul><li><p>c${oeTab()}d${oeTab()}</p>` +
                `<ul><li>${oeTab()}e${oeTab()}</li></ul></li></ul></li>` +
                `</ul>` +
                `<blockquote>${oeTab()}f${oeTab()}]g</blockquote>`,
            stepFunction: keydownShiftTab,
            contentAfterEdit:
                `<p>${oeTab(TAB_WIDTH, false)}a[${oeTab(tabAfterA, false)}b${oeTab(
                    tabAfterB,
                    false
                )}</p>` +
                `<ul>` +
                `<li><p>c${oeTab(tabAfterCinLI, false)}d${oeTab(tabAfterD, false)}</p>` +
                `<ul><li>${oeTab(tabInNestedList, false)}e${oeTab(
                    tabAfterE,
                    false
                )}</li></ul></li>` +
                `</ul>` +
                `<blockquote>f${oeTab(tabAfterFinBlockquote, false)}]g</blockquote>`,
            contentAfter:
                `<p>${oeTab(TAB_WIDTH)}a[${oeTab(tabAfterA)}b${oeTab(tabAfterB)}</p>` +
                `<ul>` +
                `<li><p>c${oeTab(tabAfterCinLI)}d${oeTab(tabAfterD)}</p>` +
                `<ul><li>${oeTab(tabInNestedList)}e${oeTab(tabAfterE)}</li></ul></li>` +
                `</ul>` +
                `<blockquote>f${oeTab(tabAfterFinBlockquote)}]g</blockquote>`,
        });
    });

    test("should remove a tab character from formatted text", async () => {
        await testEditor({
            contentBefore: `<p><strong>${oeTab()}a[]b</strong></p>`,
            stepFunction: keydownShiftTab,
            contentAfter: `<p><strong>a[]b</strong></p>`,
        });
    });

    test("should remove tab characters from the beginning of two separate formatted paragraphs", async () => {
        await testEditor({
            contentBefore:
                `<p>${oeTab()}<strong>a[b</strong></p>` + `<p>${oeTab()}<strong>c]d</strong></p>`,
            stepFunction: keydownShiftTab,
            contentAfter: `<p><strong>a[b</strong></p>` + `<p><strong>c]d</strong></p>`,
        });
    });

    test("should remove a tab character from styled text", async () => {
        await testEditor({
            contentBefore: `<p><font style="background-color: rgb(255,255,0);">${oeTab()}a[]b</font></p>`,
            stepFunction: keydownShiftTab,
            contentAfter: `<p><font style="background-color: rgb(255,255,0);">a[]b</font></p>`,
        });
    });
});

describe("update tab width", () => {
    test("should update tab width on content change", async () => {
        const tabAfterA = TAB_WIDTH - getCharWidth("p", "a");
        const tabAfterAA = TAB_WIDTH - 2 * getCharWidth("p", "a");
        await testEditor({
            contentBefore: `<p><span>a[]</span>${oeTab(tabAfterA)}</p>`,
            stepFunction: async (editor) => {
                await insertText(editor, "a");
            },
            contentAfter: `<p><span>aa[]</span>${oeTab(tabAfterAA)}</p>`,
        });
    });
});
