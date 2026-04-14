import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import { deleteBackward, deleteForward, insertText, undo } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";
import { execCommand } from "./_helpers/userCommands";
import { processThroughNormalize } from "./_helpers/dispatch";

function insertFontAwesome(faClass) {
    return (editor) => {
        execCommand(editor, "insertFontAwesome", { faClass });
    };
}

describe("parse/render", () => {
    test("should parse an oi icon", async () => {
        await testEditor({
            contentBefore: '<p><i class="oi" data-icon="pastafarianism"></i></p>',
            contentBeforeEdit:
                '<p>\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff</p>',
            contentAfter: '<p><i class="oi" data-icon="pastafarianism"></i></p>',
        });
    });

    test("should parse an oi brand icon (oi_* data-icon)", async () => {
        await testEditor({
            contentBefore: '<p><i class="oi" data-icon="oi_facebook"></i></p>',
            contentBeforeEdit:
                '<p>\ufeff<i class="oi" data-icon="oi_facebook" contenteditable="false">\u200b</i>\ufeff</p>',
            contentAfter: '<p><i class="oi" data-icon="oi_facebook"></i></p>',
        });
    });

    test("should parse an oi filled icon", async () => {
        await testEditor({
            contentBefore: '<p><i class="oi oi-filled" data-icon="star"></i></p>',
            contentBeforeEdit:
                '<p>\ufeff<i class="oi oi-filled" data-icon="star" contenteditable="false">\u200b</i>\ufeff</p>',
            contentAfter: '<p><i class="oi oi-filled" data-icon="star"></i></p>',
        });
    });

    test("should parse an oi fixed-width icon", async () => {
        await testEditor({
            contentBefore: '<p><i class="oi oi-fw" data-icon="star"></i></p>',
            contentBeforeEdit:
                '<p>\ufeff<i class="oi oi-fw" data-icon="star" contenteditable="false">\u200b</i>\ufeff</p>',
            contentAfter: '<p><i class="oi oi-fw" data-icon="star"></i></p>',
        });
    });

    test("should parse an oi icon in a <span>", async () => {
        await testEditor({
            contentBefore: '<p><span class="oi" data-icon="home"></span></p>',
            contentBeforeEdit:
                '<p>\ufeff<span class="oi" data-icon="home" contenteditable="false">\u200b</span>\ufeff</p>',
            contentAfter: '<p><span class="oi" data-icon="home"></span></p>',
        });
    });

    test("should parse an oi icon in a <span> with oi-* modifier class", async () => {
        await testEditor({
            contentBefore: '<p><span class="oi oi-pastafarianism"></span></p>',
            contentBeforeEdit:
                '<p>\ufeff<span class="oi oi-pastafarianism" contenteditable="false">\u200b</span>\ufeff</p>',
            contentAfter: '<p><span class="oi oi-pastafarianism"></span></p>',
        });
    });

    test("should parse an oi icon in a <i> with oi-* modifier class", async () => {
        await testEditor({
            contentBefore: '<p><i class="oi oi-pastafarianism"></i></p>',
            contentBeforeEdit:
                '<p>\ufeff<i class="oi oi-pastafarianism" contenteditable="false">\u200b</i>\ufeff</p>',
            contentAfter: '<p><i class="oi oi-pastafarianism"></i></p>',
        });
    });

    test("should parse an oi icon with more classes", async () => {
        await testEditor({
            contentBefore: '<p><i class="red oi bordered big" data-icon="pastafarianism"></i></p>',
            contentBeforeEdit:
                '<p>\ufeff<i class="red oi bordered big" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff</p>',
            contentAfter: '<p><i class="red oi bordered big" data-icon="pastafarianism"></i></p>',
        });
    });

    test("should parse an oi icon with multi-line classes", async () => {
        await testEditor({
            contentBefore: `<p><i class="oi
                                extra-class" data-icon="pastafarianism"></i></p>`,
            contentBeforeEdit: `<p>\ufeff<i class="oi
                                extra-class" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff</p>`,
            contentAfter: `<p><i class="oi
                                extra-class" data-icon="pastafarianism"></i></p>`,
        });
    });

    test("should parse an oi icon with more multi-line classes", async () => {
        await testEditor({
            contentBefore: `<p><i class="red oi bordered
                                big extra-class scary" data-icon="pastafarianism"></i></p>`,
            contentBeforeEdit: `<p>\ufeff<i class="red oi bordered
                                big extra-class scary" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff</p>`,
            contentAfter: `<p><i class="red oi bordered
                                big extra-class scary" data-icon="pastafarianism"></i></p>`,
        });
    });

    test("should parse an oi icon at the beginning of a paragraph", async () => {
        await testEditor({
            contentBefore: '<p><i class="oi" data-icon="pastafarianism"></i>a[b]c</p>',
            contentBeforeEdit:
                '<p>\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffa[b]c</p>',
            contentAfter: '<p><i class="oi" data-icon="pastafarianism"></i>a[b]c</p>',
        });
    });

    test("should parse an oi icon in the middle of a paragraph", async () => {
        await testEditor({
            contentBefore: '<p>a[b]c<i class="oi" data-icon="pastafarianism"></i>def</p>',
            contentBeforeEdit:
                '<p>a[b]c\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffdef</p>',
            contentAfter: '<p>a[b]c<i class="oi" data-icon="pastafarianism"></i>def</p>',
        });
    });

    test("should parse an oi icon at the end of a paragraph", async () => {
        await testEditor({
            contentBefore: '<p>a[b]c<i class="oi" data-icon="pastafarianism"></i></p>',
            contentBeforeEdit:
                '<p>a[b]c\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff</p>',
            contentAfter: '<p>a[b]c<i class="oi" data-icon="pastafarianism"></i></p>',
        });
    });

    test("should not add U+FEFF characters around icons not within a paragraph related element or a base container", async () => {
        await testEditor({
            contentBefore: '<div><i class="oi" data-icon="pastafarianism"></i><div><p>abc</p></div></div>',
            contentBeforeEdit:
                '<p data-selection-placeholder=""><br></p>' +
                '<div><i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i><div><p>abc</p></div></div>' +
                '<p data-selection-placeholder=""><br></p>',
            contentAfter: '<div><i class="oi" data-icon="pastafarianism"></i><div><p>abc</p></div></div>',
        });
    });

    test("should add U+FEFF characters around icon within a span which is within a paragraph related element or a base container", async () => {
        await testEditor({
            contentBefore: '<p><span><i class="oi" data-icon="pastafarianism"></i></span></p>',
            contentBeforeEdit:
                '<p><span>\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff</span></p>',
            contentAfter: '<p><span><i class="oi" data-icon="pastafarianism"></i></span></p>',
        });
    });

    test("should not add U+FEFF characters around icon if not direct child of paragraph related element or formatable tag", async () => {
        const { editor, el } = await setupEditor(`<p></p>`);
        const div = document.createElement("div");
        const icon = document.createElement("i");
        icon.className = "oi";
        icon.dataset.icon = "pastafarianism";
        div.appendChild(icon);
        el.firstChild.appendChild(div);
        processThroughNormalize(editor);
        expect(getContent(el)).toBe(
            `<p><div><i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i></div></p>`
        );
    });
});

describe("deleteForward", () => {
    describe("Selection collapsed", () => {
        describe("Basic", () => {
            test("should delete an icon (deleteForward, collapsed)", async () => {
                await testEditor({
                    contentBefore: '<p>ab[]<i class="oi" data-icon="pastafarianism"></i>cd</p>',
                    contentBeforeEdit:
                        '<p>ab[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffcd</p>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });

            test("should not delete an icon", async () => {
                await testEditor({
                    contentBefore: '<p>ab<i class="oi" data-icon="pastafarianism"></i>[]cd</p>',
                    contentBeforeEdit:
                        '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff[]cd</p>',
                    stepFunction: deleteForward,
                    contentAfterEdit:
                        '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff[]d</p>',
                    contentAfter: '<p>ab<i class="oi" data-icon="pastafarianism"></i>[]d</p>',
                });
            });

            test("should not delete an icon after multiple deleteForward", async () => {
                await testEditor({
                    contentBefore: '<p>ab[]cde<i class="oi" data-icon="pastafarianism"></i>fghij</p>',
                    contentBeforeEdit:
                        '<p>ab[]cde\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufefffghij</p>',
                    stepFunction: async (editor) => {
                        deleteForward(editor);
                        deleteForward(editor);
                        deleteForward(editor);
                    },
                    contentAfterEdit:
                        '<p>ab[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufefffghij</p>',
                    contentAfter: '<p>ab[]<i class="oi" data-icon="pastafarianism"></i>fghij</p>',
                });
            });

            test("should not delete an icon after one deleteForward with spaces", async () => {
                await testEditor({
                    contentBefore: '<p>ab[] <i class="oi" data-icon="pastafarianism"></i> cd</p>',
                    contentBeforeEdit:
                        '<p>ab[] \ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff cd</p>',
                    stepFunction: async (editor) => {
                        deleteForward(editor);
                    },
                    contentAfterEdit:
                        '<p>ab[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff cd</p>',
                    contentAfter: '<p>ab[]<i class="oi" data-icon="pastafarianism"></i> cd</p>',
                });
            });

            test("should not delete an icon after multiple deleteForward with spaces", async () => {
                await testEditor({
                    contentBefore: '<p>a[]b <i class="oi" data-icon="pastafarianism"></i> cd</p>',
                    contentBeforeEdit:
                        '<p>a[]b \ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff cd</p>',
                    stepFunction: async (editor) => {
                        deleteForward(editor);
                        deleteForward(editor);
                    },
                    contentAfterEdit:
                        '<p>a[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff cd</p>',
                    contentAfter: '<p>a[]<i class="oi" data-icon="pastafarianism"></i> cd</p>',
                });
            });

            test("should not delete an icon after multiple deleteForward with spaces inside a <span>", async () => {
                await testEditor({
                    contentBefore:
                        '<p><span class="a">ab[]c </span><i class="oi" data-icon="star"></i> def</p>',
                    contentBeforeEdit:
                        '<p><span class="a">ab[]c </span>\ufeff<i class="oi" data-icon="star" contenteditable="false">\u200b</i>\ufeff def</p>',
                    stepFunction: async (editor) => {
                        deleteForward(editor);
                        deleteForward(editor);
                    },
                    contentAfterEdit:
                        '<p><span class="a">ab[]</span>\ufeff<i class="oi" data-icon="star" contenteditable="false">\u200b</i>\ufeff def</p>',
                    contentAfter:
                        '<p><span class="a">ab[]</span><i class="oi" data-icon="star"></i> def</p>',
                });
            });
        });
    });

    describe("Selection not collapsed", () => {
        describe("Basic", () => {
            test("should delete an icon (forward selection, deleteForward, !collapsed)", async () => {
                await testEditor({
                    contentBefore: '<p>ab[<i class="oi" data-icon="pastafarianism"></i>]cd</p>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });
            test("should delete an icon (backward selection, deleteForward, !collapsed)", async () => {
                await testEditor({
                    contentBefore: '<p>ab]<i class="oi" data-icon="pastafarianism"></i>[cd</p>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });
        });
    });
});

describe("deleteBackward", () => {
    describe("Selection collapsed", () => {
        describe("Basic", () => {
            test("should delete an icon (deleteBackward, collapsed) (1)", async () => {
                await testEditor({
                    contentBefore: '<p>ab<i class="oi" data-icon="pastafarianism"></i>[]cd</p>',
                    contentBeforeEdit:
                        '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff[]cd</p>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });

            test("should delete an icon (deleteBackward, collapsed) (2)", async () => {
                await testEditor({
                    contentBefore: '<p>ab<i class="oi oi-pastafarianism"></i>[]cd</p>',
                    contentBeforeEdit:
                        '<p>ab\ufeff<i class="oi oi-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]cd</p>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });

            test("should delete an icon before a span", async () => {
                await testEditor({
                    contentBefore:
                        '<p>ab<i class="oi" data-icon="pastafarianism"></i><span class="a">[]cd</span></p>',
                    contentBeforeEdit:
                        '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff<span class="a">[]cd</span></p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab[]<span class="a">cd</span></p>',
                });
            });

            test("should not delete an icon before a span", async () => {
                await testEditor({
                    contentBefore:
                        '<p>ab<i class="oi" data-icon="pastafarianism"></i><span class="a">c[]d</span></p>',
                    contentBeforeEdit:
                        '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff<span class="a">c[]d</span></p>',
                    stepFunction: deleteBackward,
                    contentAfterEdit:
                        '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff<span class="a">[]d</span></p>',
                    contentAfter:
                        '<p>ab<i class="oi" data-icon="pastafarianism"></i><span class="a">[]d</span></p>',
                });
            });

            test("should not delete an icon", async () => {
                await testEditor({
                    contentBefore: '<p>ab[]<i class="oi" data-icon="pastafarianism"></i>cd</p>',
                    contentBeforeEdit:
                        '<p>ab[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffcd</p>',
                    stepFunction: deleteBackward,
                    contentAfterEdit:
                        '<p>a[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffcd</p>',
                    contentAfter: '<p>a[]<i class="oi" data-icon="pastafarianism"></i>cd</p>',
                });
            });

            test("should not delete an icon after multiple deleteBackward", async () => {
                await testEditor({
                    contentBefore: '<p>abcde<i class="oi" data-icon="pastafarianism"></i>fgh[]ij</p>',
                    contentBeforeEdit:
                        '<p>abcde\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufefffgh[]ij</p>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfterEdit:
                        '<p>abcde\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff[]ij</p>',
                    contentAfter: '<p>abcde<i class="oi" data-icon="pastafarianism"></i>[]ij</p>',
                });
            });

            test("should not delete an icon after multiple deleteBackward with spaces", async () => {
                await testEditor({
                    contentBefore: '<p>abcde <i class="oi" data-icon="pastafarianism"></i> fg[]hij</p>',
                    contentBeforeEdit:
                        '<p>abcde \ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff fg[]hij</p>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfterEdit:
                        '<p>abcde \ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff[]hij</p>',
                    contentAfter: '<p>abcde <i class="oi" data-icon="pastafarianism"></i>[]hij</p>',
                });
            });
        });
    });
    describe("Selection not collapsed", () => {
        describe("Basic", () => {
            test("should delete an icon (forward selection, deleteBackward, !collapsed)", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: '<p>ab[<i class="oi" data-icon="pastafarianism"></i>]cd</p>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });
            test("should delete an icon (backward selection, deleteBackward, !collapsed)", async () => {
                // Backward selection
                await testEditor({
                    contentBefore: '<p>ab]<i class="oi" data-icon="pastafarianism"></i>[cd</p>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });
        });
    });
});

describe("FontAwesome insertion (legacy insertFontAwesome command)", () => {
    test("should insert a fontAwesome at the start of an element", async () => {
        await testEditor({
            contentBefore: "<p>[]abc</p>",
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>\ufeff<i class="fa fa-star" contenteditable="false">\u200b</i>[]\ufeffabc</p>',
            contentAfter: '<p><i class="fa fa-star"></i>[]abc</p>',
        });
    });

    test("should insert a fontAwesome within an element", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd</p>",
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>ab\ufeff<i class="fa fa-star" contenteditable="false">\u200b</i>[]\ufeffcd</p>',
            contentAfter: '<p>ab<i class="fa fa-star"></i>[]cd</p>',
        });
    });

    test("should insert a fontAwesome at the end of an element", async () => {
        await testEditor({
            contentBefore: "<p>abc[]</p>",
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>abc\ufeff<i class="fa fa-star" contenteditable="false">\u200b</i>[]\ufeff</p>',
            contentAfter: '<p>abc<i class="fa fa-star"></i>[]</p>',
        });
    });

    test("should insert a fontAwesome after an oi icon", async () => {
        await testEditor({
            contentBefore: '<p>ab<i class="oi" data-icon="pastafarianism"></i>c[]d</p>',
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffc\ufeff<i class="fa fa-star" contenteditable="false">\u200b</i>[]\ufeffd</p>',
            contentAfter:
                '<p>ab<i class="oi" data-icon="pastafarianism"></i>c<i class="fa fa-star"></i>[]d</p>',
        });
    });

    test("should insert a fontAwesome before an oi icon", async () => {
        await testEditor({
            contentBefore: '<p>ab[]<i class="oi" data-icon="pastafarianism"></i>cd</p>',
            contentBeforeEdit:
                '<p>ab[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffcd</p>',
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>ab\ufeff<i class="fa fa-star" contenteditable="false">\u200b</i>[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffcd</p>',
            contentAfter:
                '<p>ab<i class="fa fa-star"></i>[]<i class="oi" data-icon="pastafarianism"></i>cd</p>',
        });
    });
    test.skip("should insert a fontAwesome and replace the icon", async () => {
        await testEditor({
            contentBefore: '<p>ab[<i class="oi" data-icon="pastafarianism"></i>]cd</p>',
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfter: '<p>abs<i class="fa fa-star"></i>[]cd</p>',
        });
    });

    test("should insert fontAwesome consecutively", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                execCommand(editor, "insertFontAwesome", { faClass: "fa fa-star" });
                execCommand(editor, "insertFontAwesome", { faClass: "fa fa-glass" });
            },
            contentAfterEdit:
                '<p>\ufeff<i class="fa fa-star" contenteditable="false">\u200b</i>\ufeff<i class="fa fa-glass" contenteditable="false">\u200b</i>[]\ufeff</p>',
            contentAfter: '<p><i class="fa fa-star"></i><i class="fa fa-glass"></i>[]</p>',
        });
    });
});

describe("Text insertion", () => {
    test("should insert a character before an icon", async () => {
        await testEditor({
            contentBefore: '<p>ab[]<i class="oi" data-icon="pastafarianism"></i>cd</p>',
            contentBeforeEdit:
                '<p>ab[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffcd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "s");
            },
            contentAfterEdit:
                '<p>abs[]\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffcd</p>',
            contentAfter: '<p>abs[]<i class="oi" data-icon="pastafarianism"></i>cd</p>',
        });
    });

    test("should insert a character after an icon", async () => {
        await testEditor({
            contentBefore: '<p>ab<i class="oi" data-icon="pastafarianism"></i>[]cd</p>',
            contentBeforeEdit:
                '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff[]cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "s");
            },
            contentAfterEdit:
                '<p>ab\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeffs[]cd</p>',
            contentAfter: '<p>ab<i class="oi" data-icon="pastafarianism"></i>s[]cd</p>',
        });
    });
    test.skip("should insert a character and replace the icon", async () => {
        await testEditor({
            contentBefore: '<p>ab[<i class="oi" data-icon="pastafarianism"></i>]cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "s");
            },
            contentAfter: "<p>abs[]cd</p>",
        });
    });

    test("undo shouldn't remove changes applied by the editor setup", async () => {
        const { el, editor } = await setupEditor(
            `<p><i class="oi" data-icon="pastafarianism"></i></p>`
        );
        expect(getContent(el)).toBe(
            `<p>\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff</p>`
        );
        undo(editor);
        expect(getContent(el)).toBe(
            `<p>\ufeff<i class="oi" data-icon="pastafarianism" contenteditable="false">\u200b</i>\ufeff</p>`
        );
    });
});

describe("Legacy FA → OI migration", () => {
    test("should migrate a known Material Symbols icon (fa fa-star → oi data-icon=star)", async () => {
        const { el } = await setupEditor('<p><i class="fa fa-star"></i></p>');
        expect(getContent(el)).toBe(
            '<p>\ufeff<i class="oi" data-icon="star" contenteditable="false">\u200b</i>\ufeff</p>'
        );
    });

    test("should migrate a known brand icon (fa fa-facebook → oi data-icon=oi_facebook)", async () => {
        const { el } = await setupEditor('<p><i class="fa fa-facebook"></i></p>');
        expect(getContent(el)).toBe(
            '<p>\ufeff<i class="oi" data-icon="oi_facebook" contenteditable="false">\u200b</i>\ufeff</p>'
        );
    });

    test("should convert a fa size modifier class (fa-2x → oi-2x) and migrate the icon", async () => {
        const { el } = await setupEditor('<p><i class="fa fa-star fa-2x"></i></p>');
        expect(getContent(el)).toBe(
            '<p>\ufeff<i class="oi-2x oi" data-icon="star" contenteditable="false">\u200b</i>\ufeff</p>'
        );
    });

    test("should convert a fa-fw modifier class and migrate the icon", async () => {
        const { el } = await setupEditor('<p><i class="fa fa-pencil fa-fw"></i></p>');
        expect(getContent(el)).toBe(
            '<p>\ufeff<i class="oi-fw oi" data-icon="edit" contenteditable="false">\u200b</i>\ufeff</p>'
        );
    });

    test("should strip fa classes when icon name is not in the mapping", async () => {
        // Unknown icon name: fa and fa-* classes are removed, but no oi class or data-icon
        // is added — the element loses its icon identity and is no longer matched by ICON_SELECTOR.
        const { el } = await setupEditor('<p><i class="fa fa-pastafarianism"></i></p>');
        expect(getContent(el)).toBe('<p><i class=""></i></p>');
    });

    test("undo should not revert migration (migration runs before history tracking)", async () => {
        const { el, editor } = await setupEditor('<p><i class="fa fa-star"></i></p>');
        // Verify migration happened
        expect(getContent(el)).toBe(
            '<p>\ufeff<i class="oi" data-icon="star" contenteditable="false">\u200b</i>\ufeff</p>'
        );
        undo(editor);
        // Still migrated — setup() runs before the history/dirty system is active
        expect(getContent(el)).toBe(
            '<p>\ufeff<i class="oi" data-icon="star" contenteditable="false">\u200b</i>\ufeff</p>'
        );
    });
});
