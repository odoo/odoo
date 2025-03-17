import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import { deleteBackward, deleteForward, insertText, undo } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";
import { execCommand } from "./_helpers/userCommands";

function insertFontAwesome(faClass) {
    return (editor) => {
        execCommand(editor, "insertFontAwesome", { faClass });
    };
}

describe("parse/render", () => {
    test("should parse an old-school fontawesome", async () => {
        await testEditor({
            contentBefore: '<p><i class="fa fa-star"></i></p>',
            contentBeforeEdit: '<p><i class="fa fa-star" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="fa fa-star"></i></p>',
        });
    });

    test("should parse a brand fontawesome", async () => {
        await testEditor({
            contentBefore: '<p><i class="fab fa-opera"></i></p>',
            contentBeforeEdit: '<p><i class="fab fa-opera" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="fab fa-opera"></i></p>',
        });
    });

    test("should parse a duotone fontawesome", async () => {
        await testEditor({
            contentBefore: '<p><i class="fad fa-bus-alt"></i></p>',
            contentBeforeEdit:
                '<p><i class="fad fa-bus-alt" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="fad fa-bus-alt"></i></p>',
        });
    });

    test("should parse a light fontawesome", async () => {
        await testEditor({
            contentBefore: '<p><i class="fab fa-accessible-icon"></i></p>',
            contentBeforeEdit:
                '<p><i class="fab fa-accessible-icon" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="fab fa-accessible-icon"></i></p>',
        });
    });

    test("should parse a regular fontawesome", async () => {
        await testEditor({
            contentBefore: '<p><i class="far fa-money-bill-alt"></i></p>',
            contentBeforeEdit:
                '<p><i class="far fa-money-bill-alt" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="far fa-money-bill-alt"></i></p>',
        });
    });

    test("should parse a solid fontawesome", async () => {
        await testEditor({
            // @phoenix content adapted to make it valid html
            contentBefore: '<p><i class="fa fa-pastafarianism"></i></p>',
            contentBeforeEdit:
                '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="fa fa-pastafarianism"></i></p>',
        });
    });

    test("should parse a fontawesome in a <span>", async () => {
        await testEditor({
            contentBefore: '<p><span class="fa fa-pastafarianism"></span></p>',
            contentBeforeEdit:
                '<p><span class="fa fa-pastafarianism" contenteditable="false">\u200b</span></p>',
            contentAfter: '<p><span class="fa fa-pastafarianism"></span></p>',
        });
        await testEditor({
            contentBefore: '<p><span class="oi oi-pastafarianism"></span></p>',
            contentBeforeEdit:
                '<p><span class="oi oi-pastafarianism" contenteditable="false">\u200b</span></p>',
            contentAfter: '<p><span class="oi oi-pastafarianism"></span></p>',
        });
    });

    test("should parse a fontawesome in a <i>", async () => {
        await testEditor({
            // @phoenix content adapted to make it valid html
            contentBefore: '<p><i class="fa fa-pastafarianism"></i></p>',
            contentBeforeEdit:
                '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="fa fa-pastafarianism"></i></p>',
        });
        await testEditor({
            // @phoenix content adapted to make it valid html
            contentBefore: '<p><i class="oi oi-pastafarianism"></i></p>',
            contentBeforeEdit:
                '<p><i class="oi oi-pastafarianism" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="oi oi-pastafarianism"></i></p>',
        });
    });

    test("should parse a fontawesome with more classes", async () => {
        await testEditor({
            contentBefore: '<p><i class="red fa bordered fa-pastafarianism big"></i></p>',
            contentBeforeEdit:
                '<p><i class="red fa bordered fa-pastafarianism big" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p><i class="red fa bordered fa-pastafarianism big"></i></p>',
        });
    });

    test("should parse a fontawesome with multi-line classes", async () => {
        await testEditor({
            contentBefore: `<p><i class="fa
                                fa-pastafarianism"></i></p>`,
            contentBeforeEdit: `<p><i class="fa
                                fa-pastafarianism" contenteditable="false">\u200b</i></p>`,
            contentAfter: `<p><i class="fa
                                fa-pastafarianism"></i></p>`,
        });
    });

    test("should parse a fontawesome with more multi-line classes", async () => {
        await testEditor({
            contentBefore: `<p><i class="red fa bordered
                                big fa-pastafarianism scary"></i></p>`,
            contentBeforeEdit: `<p><i class="red fa bordered
                                big fa-pastafarianism scary" contenteditable="false">\u200b</i></p>`,
            contentAfter: `<p><i class="red fa bordered
                                big fa-pastafarianism scary"></i></p>`,
        });
    });

    test("should parse a fontawesome at the beginning of a paragraph", async () => {
        await testEditor({
            contentBefore: '<p><i class="fa fa-pastafarianism"></i>a[b]c</p>',
            contentBeforeEdit:
                '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>a[b]c</p>',
            contentAfter: '<p><i class="fa fa-pastafarianism"></i>a[b]c</p>',
        });
    });

    test("should parse a fontawesome in the middle of a paragraph", async () => {
        await testEditor({
            contentBefore: '<p>a[b]c<i class="fa fa-pastafarianism"></i>def</p>',
            contentBeforeEdit:
                '<p>a[b]c<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>def</p>',
            contentAfter: '<p>a[b]c<i class="fa fa-pastafarianism"></i>def</p>',
        });
    });

    test("should parse a fontawesome at the end of a paragraph", async () => {
        await testEditor({
            contentBefore: '<p>a[b]c<i class="fa fa-pastafarianism"></i></p>',
            contentBeforeEdit:
                '<p>a[b]c<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i></p>',
            contentAfter: '<p>a[b]c<i class="fa fa-pastafarianism"></i></p>',
        });
    });
    /** not sure this is necessary, keep for now in case it is
        test('should insert navigation helpers when before a fontawesome, in an editable', async () => {
            await testEditor({
                contentBefore: '<p>abc[]<i class="fa fa-pastafarianism"></i></p>',
                contentAfter:
                    '<p>abc[]\u200B<i class="fa fa-pastafarianism" contenteditable="false"></i>\u200B</p>',
            });
            await testEditor({
                contentBefore: '<p>[]<i class="fa fa-pastafarianism"></i></p>',
                contentAfter:
                    '<p>\u200B[]<i class="fa fa-pastafarianism" contenteditable="false"></i>\u200B</p>',
            });
        });
        test('should insert navigation helpers when after a fontawesome, in an editable', async () => {
            await testEditor({
                contentBefore: '<p><i class="fa fa-pastafarianism"></i>[]abc</p>',
                contentAfter:
                    '<p>\u200B<i class="fa fa-pastafarianism" contenteditable="false"></i>\u200B[]abc</p>',
            });
            await testEditor({
                contentBefore: '<p><i class="fa fa-pastafarianism"></i>[]</p>',
                contentAfter:
                    '<p>\u200B<i class="fa fa-pastafarianism" contenteditable="false"></i>\u200B[]</p>',
            });
        });
        test('should not insert navigation helpers when not adjacent to a fontawesome, in an editable', async () => {
            await testEditor({
                contentBefore: '<p>ab[]c<i class="fa fa-pastafarianism"></i></p>',
                contentAfter:
                    '<p>ab[]c<i class="fa fa-pastafarianism" contenteditable="false"></i></p>',
            });
            await testEditor({
                contentBefore: '<p><i class="fa fa-pastafarianism"></i>a[]bc</p>',
                contentAfter:
                    '<p><i class="fa fa-pastafarianism" contenteditable="false"></i>a[]bc</p>',
            });
        });
        test('should not insert navigation helpers when adjacent to a fontawesome in contenteditable=false container', async () => {
            await testEditor({
                contentBefore:
                    '<p contenteditable="false">abc[]<i class="fa fa-pastafarianism"></i></p>',
                contentAfter:
                    '<p contenteditable="false">abc<i class="fa fa-pastafarianism" contenteditable="false"></i></p>',
            });
            await testEditor({
                contentBefore:
                    '<p contenteditable="false"><i class="fa fa-pastafarianism"></i>[]abc</p>',
                contentAfter:
                    '<p contenteditable="false"><i class="fa fa-pastafarianism" contenteditable="false"></i>abc</p>',
            });
        });
        test('should not insert navigation helpers when adjacent to a fontawesome in contenteditable=false format', async () => {
            await testEditor({
                contentBefore:
                    '<p contenteditable="true"><b contenteditable="false">abc[]<i class="fa fa-pastafarianism"></i></b></p>',
                contentAfter:
                    '<p contenteditable="true"><b contenteditable="false">abc<i class="fa fa-pastafarianism" contenteditable="false"></i></b></p>',
            });
            await testEditor({
                contentBefore:
                    '<p contenteditable="true"><b contenteditable="false"><i class="fa fa-pastafarianism"></i>[]abc</b></p>',
                contentAfter:
                    '<p contenteditable="true"><b contenteditable="false"><i class="fa fa-pastafarianism" contenteditable="false"></i>abc</b></p>',
            });
        });
        test('should not insert navigation helpers when adjacent to a fontawesome in contenteditable=false format (oe-nested)', async () => {
            await testEditor({
                contentBefore:
                    '<p contenteditable="true"><a contenteditable="true"><b contenteditable="false">abc[]<i class="fa fa-pastafarianism"></i></b></a></p>',
                contentAfter:
                    '<p contenteditable="true"><a contenteditable="true"><b contenteditable="false">abc<i class="fa fa-pastafarianism" contenteditable="false"></i></b></a></p>',
            });
            await testEditor({
                contentBefore:
                    '<p contenteditable="true"><a contenteditable="true"><b contenteditable="false"><i class="fa fa-pastafarianism"></i>[]abc</b></a></p>',
                contentAfter:
                    '<p contenteditable="true"><a contenteditable="true"><b contenteditable="false"><i class="fa fa-pastafarianism" contenteditable="false"></i>abc</b></a></p>',
            });
        });*/
});

describe("deleteForward", () => {
    describe("Selection collapsed", () => {
        describe("Basic", () => {
            test("should delete a fontawesome (deleteForward, collapsed)", async () => {
                await testEditor({
                    contentBefore: '<p>ab[]<i class="fa fa-pastafarianism"></i>cd</p>',
                    contentBeforeEdit:
                        '<p>ab[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>cd</p>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });

            test("should not delete a fontawesome", async () => {
                await testEditor({
                    contentBefore: '<p>ab<i class="fa fa-pastafarianism"></i>[]cd</p>',
                    contentBeforeEdit:
                        '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]cd</p>',
                    stepFunction: deleteForward,
                    contentAfterEdit:
                        '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]d</p>',
                    contentAfter: '<p>ab<i class="fa fa-pastafarianism"></i>[]d</p>',
                });
            });

            test("should not delete a fontawesome after multiple deleteForward", async () => {
                await testEditor({
                    contentBefore: '<p>ab[]cde<i class="fa fa-pastafarianism"></i>fghij</p>',
                    contentBeforeEdit:
                        '<p>ab[]cde<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>fghij</p>',
                    stepFunction: async (editor) => {
                        deleteForward(editor);
                        deleteForward(editor);
                        deleteForward(editor);
                    },
                    contentAfterEdit:
                        '<p>ab[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>fghij</p>',
                    contentAfter: '<p>ab[]<i class="fa fa-pastafarianism"></i>fghij</p>',
                });
            });

            test("should not delete a fontawesome after one deleteForward with spaces", async () => {
                await testEditor({
                    contentBefore: '<p>ab[] <i class="fa fa-pastafarianism"></i> cd</p>',
                    contentBeforeEdit:
                        '<p>ab[] <i class="fa fa-pastafarianism" contenteditable="false">\u200b</i> cd</p>',
                    stepFunction: async (editor) => {
                        deleteForward(editor);
                    },
                    contentAfterEdit:
                        '<p>ab[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i> cd</p>',
                    contentAfter: '<p>ab[]<i class="fa fa-pastafarianism"></i> cd</p>',
                });
            });

            test("should not delete a fontawesome after multiple deleteForward with spaces", async () => {
                await testEditor({
                    contentBefore: '<p>a[]b <i class="fa fa-pastafarianism"></i> cd</p>',
                    contentBeforeEdit:
                        '<p>a[]b <i class="fa fa-pastafarianism" contenteditable="false">\u200b</i> cd</p>',
                    stepFunction: async (editor) => {
                        deleteForward(editor);
                        deleteForward(editor);
                    },
                    contentAfterEdit:
                        '<p>a[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i> cd</p>',
                    contentAfter: '<p>a[]<i class="fa fa-pastafarianism"></i> cd</p>',
                });
            });

            test("should not delete a fontawesome after multiple deleteForward with spaces inside a <span>", async () => {
                await testEditor({
                    contentBefore:
                        '<p><span class="a">ab[]c </span><i class="fa fa-star"></i> def</p>',
                    contentBeforeEdit:
                        '<p><span class="a">ab[]c </span><i class="fa fa-star" contenteditable="false">\u200b</i> def</p>',
                    stepFunction: async (editor) => {
                        deleteForward(editor);
                        deleteForward(editor);
                    },
                    contentAfterEdit:
                        '<p><span class="a">ab[]</span><i class="fa fa-star" contenteditable="false">\u200b</i> def</p>',
                    contentAfter:
                        '<p><span class="a">ab[]</span><i class="fa fa-star"></i> def</p>',
                });
            });
        });
    });

    describe("Selection not collapsed", () => {
        describe("Basic", () => {
            test("should delete a fontawesome (forward selection, deleteForward, !collapsed)", async () => {
                await testEditor({
                    contentBefore: '<p>ab[<i class="fa fa-pastafarianism"></i>]cd</p>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });
            test("should delete a fontawesome (backward selection, deleteForward, !collapsed)", async () => {
                await testEditor({
                    contentBefore: '<p>ab]<i class="fa fa-pastafarianism"></i>[cd</p>',
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
            test("should delete a fontawesome (deleteBackward, collapsed)", async () => {
                await testEditor({
                    contentBefore: '<p>ab<i class="fa fa-pastafarianism"></i>[]cd</p>',
                    contentBeforeEdit:
                        '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]cd</p>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
                await testEditor({
                    contentBefore: '<p>ab<i class="oi oi-pastafarianism"></i>[]cd</p>',
                    contentBeforeEdit:
                        '<p>ab<i class="oi oi-pastafarianism" contenteditable="false">\u200b</i>[]cd</p>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });

            test("should delete a fontawesome before a span", async () => {
                await testEditor({
                    contentBefore:
                        '<p>ab<i class="fa fa-pastafarianism"></i><span class="a">[]cd</span></p>',
                    contentBeforeEdit:
                        '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i><span class="a">[]cd</span></p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab[]<span class="a">cd</span></p>',
                });
            });

            test("should not delete a fontawesome before a span", async () => {
                await testEditor({
                    contentBefore:
                        '<p>ab<i class="fa fa-pastafarianism"></i><span class="a">c[]d</span></p>',
                    contentBeforeEdit:
                        '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i><span class="a">c[]d</span></p>',
                    stepFunction: deleteBackward,
                    contentAfterEdit:
                        '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i><span class="a">[]d</span></p>',
                    contentAfter:
                        '<p>ab<i class="fa fa-pastafarianism"></i><span class="a">[]d</span></p>',
                });
            });

            test("should not delete a fontawesome", async () => {
                await testEditor({
                    contentBefore: '<p>ab[]<i class="fa fa-pastafarianism"></i>cd</p>',
                    contentBeforeEdit:
                        '<p>ab[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>cd</p>',
                    stepFunction: deleteBackward,
                    contentAfterEdit:
                        '<p>a[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>cd</p>',
                    contentAfter: '<p>a[]<i class="fa fa-pastafarianism"></i>cd</p>',
                });
            });

            test("should not delete a fontawesome after multiple deleteBackward", async () => {
                await testEditor({
                    contentBefore: '<p>abcde<i class="fa fa-pastafarianism"></i>fgh[]ij</p>',
                    contentBeforeEdit:
                        '<p>abcde<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>fgh[]ij</p>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfterEdit:
                        '<p>abcde<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]ij</p>',
                    contentAfter: '<p>abcde<i class="fa fa-pastafarianism"></i>[]ij</p>',
                });
            });

            test("should not delete a fontawesome after multiple deleteBackward with spaces", async () => {
                await testEditor({
                    contentBefore: '<p>abcde <i class="fa fa-pastafarianism"></i> fg[]hij</p>',
                    contentBeforeEdit:
                        '<p>abcde <i class="fa fa-pastafarianism" contenteditable="false">\u200b</i> fg[]hij</p>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfterEdit:
                        '<p>abcde <i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]hij</p>',
                    contentAfter: '<p>abcde <i class="fa fa-pastafarianism"></i>[]hij</p>',
                });
            });
        });
    });
    describe("Selection not collapsed", () => {
        describe("Basic", () => {
            test("should delete a fontawesome (forward selection, deleteBackward, !collapsed)", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: '<p>ab[<i class="fa fa-pastafarianism"></i>]cd</p>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });
            test("should delete a fontawesome (backward selection, deleteBackward, !collapsed)", async () => {
                // Backward selection
                await testEditor({
                    contentBefore: '<p>ab]<i class="fa fa-pastafarianism"></i>[cd</p>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
            });
        });
    });
});

describe("FontAwesome insertion", () => {
    test("should insert a fontAwesome at the start of an element", async () => {
        await testEditor({
            contentBefore: "<p>[]abc</p>",
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p><i class="fa fa-star" contenteditable="false">\u200b</i>[]abc</p>',
            contentAfter: '<p><i class="fa fa-star"></i>[]abc</p>',
        });
    });

    test("should insert a fontAwesome within an element", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd</p>",
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>ab<i class="fa fa-star" contenteditable="false">\u200b</i>[]cd</p>',
            contentAfter: '<p>ab<i class="fa fa-star"></i>[]cd</p>',
        });
    });

    test("should insert a fontAwesome at the end of an element", async () => {
        await testEditor({
            contentBefore: "<p>abc[]</p>",
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>abc<i class="fa fa-star" contenteditable="false">\u200b</i>[]</p>',
            contentAfter: '<p>abc<i class="fa fa-star"></i>[]</p>',
        });
    });

    test("should insert a fontAwesome after", async () => {
        await testEditor({
            contentBefore: '<p>ab<i class="fa fa-pastafarianism"></i>c[]d</p>',
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>c<i class="fa fa-star" contenteditable="false">\u200b</i>[]d</p>',
            contentAfter:
                '<p>ab<i class="fa fa-pastafarianism"></i>c<i class="fa fa-star"></i>[]d</p>',
        });
    });

    test("should insert a fontAwesome before", async () => {
        await testEditor({
            contentBefore: '<p>ab[]<i class="fa fa-pastafarianism"></i>cd</p>',
            contentBeforeEdit:
                '<p>ab[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>cd</p>',
            stepFunction: insertFontAwesome("fa fa-star"),
            contentAfterEdit:
                '<p>ab<i class="fa fa-star" contenteditable="false">\u200b</i>[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>cd</p>',
            contentAfter:
                '<p>ab<i class="fa fa-star"></i>[]<i class="fa fa-pastafarianism"></i>cd</p>',
        });
    });
    test.skip("should insert a fontAwesome and replace the icon", async () => {
        await testEditor({
            contentBefore: '<p>ab[<i class="fa fa-pastafarianism"></i>]cd</p>',
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
                '<p><i class="fa fa-star" contenteditable="false">\u200b</i><i class="fa fa-glass" contenteditable="false">\u200b</i>[]</p>',
            contentAfter: '<p><i class="fa fa-star"></i><i class="fa fa-glass"></i>[]</p>',
        });
    });
});

describe("Text insertion", () => {
    test("should insert a character before", async () => {
        await testEditor({
            contentBefore: '<p>ab[]<i class="fa fa-pastafarianism"></i>cd</p>',
            contentBeforeEdit:
                '<p>ab[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "s");
            },
            contentAfterEdit:
                '<p>abs[]<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>cd</p>',
            contentAfter: '<p>abs[]<i class="fa fa-pastafarianism"></i>cd</p>',
        });
    });

    test("should insert a character after", async () => {
        await testEditor({
            contentBefore: '<p>ab<i class="fa fa-pastafarianism"></i>[]cd</p>',
            contentBeforeEdit:
                '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "s");
            },
            contentAfterEdit:
                '<p>ab<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>s[]cd</p>',
            contentAfter: '<p>ab<i class="fa fa-pastafarianism"></i>s[]cd</p>',
        });
    });
    test.skip("should insert a character and replace the icon", async () => {
        await testEditor({
            contentBefore: '<p>ab[<i class="fa fa-pastafarianism"></i>]cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "s");
            },
            contentAfter: "<p>abs[]cd</p>",
        });
    });

    test("undo shouldn't remove changes applied by the editor setup", async () => {
        const { el, editor } = await setupEditor(`<p><i class="fa fa-pastafarianism"></i></p>`);
        expect(getContent(el)).toBe(
            `<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i></p>`
        );
        undo(editor);
        expect(getContent(el)).toBe(
            `<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i></p>`
        );
    });
});
