import { describe, expect, test } from "@odoo/hoot";
import { testEditor, setupEditor } from "../_helpers/editor";
import { unlinkFromPopover, unlinkByCommand, unlinkFromToolbar } from "../_helpers/user_actions";
import { getContent, setSelection } from "../_helpers/selection";

describe("range collapsed, remove by popover unlink button", () => {
    test("should remove the link if collapsed range at the end of a link", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="http://test.test/">bcd[]</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: "<p>abcd[]e</p>",
        });
        // With fontawesome at the start of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/"><span class="fa fa-music" contenteditable="false">\u200B</span>bcd[]</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a<span class="fa fa-music"></span>bcd[]e</p>',
        });
        // With fontawesome at the middle of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/">bc<span class="fa fa-music" contenteditable="false">\u200B</span>d[]</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>abc<span class="fa fa-music"></span>d[]e</p>',
        });
        // With fontawesome at the end of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/">bcd[]<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>abcd[]<span class="fa fa-music"></span>e</p>',
        });
    });

    test("should remove the link if collapsed range in the middle a link", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="http://test.test/">b[]cd</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: "<p>ab[]cde</p>",
        });
        // With fontawesome at the start of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/"><span class="fa fa-music" contenteditable="false">\u200B</span>b[]cd</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a<span class="fa fa-music"></span>b[]cde</p>',
        });
        // With fontawesome at the middle of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/">b[]c<span class="fa fa-music" contenteditable="false">\u200B</span>d</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>ab[]c<span class="fa fa-music"></span>de</p>',
        });
        // With fontawesome at the end of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/">b[]cd<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>ab[]cd<span class="fa fa-music"></span>e</p>',
        });
    });

    test("should remove the link if collapsed range at the start of a link", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="http://test.test/">[]bcd</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: "<p>a[]bcde</p>",
        });
        // With fontawesome at the start of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/"><span class="fa fa-music" contenteditable="false">\u200B</span>[]bcd</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a<span class="fa fa-music"></span>[]bcde</p>',
        });
        // With fontawesome at the middle of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/">[]bc<span class="fa fa-music" contenteditable="false">\u200B</span>d</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a[]bc<span class="fa fa-music"></span>de</p>',
        });
        // With fontawesome at the end of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="http://test.test/">[]bcd<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a[]bcd<span class="fa fa-music"></span>e</p>',
        });
    });

    test("should remove only the current link if collapsed range in the middle of a link", async () => {
        await testEditor({
            contentBefore:
                '<p><a href="http://test.test/">a</a>b<a href="http://test.test/">c[]d</a>e<a href="http://test.test/">f</a></p>',
            stepFunction: unlinkFromPopover,
            contentAfter:
                '<p><a href="http://test.test/">a</a>bc[]de<a href="http://test.test/">f</a></p>',
        });
        // With fontawesome at the start of the link.
        await testEditor({
            contentBefore:
                '<p><a href="http://test.test/">a</a>b<a href="http://test.test/"><span class="fa fa-music" contenteditable="false">\u200B</span>c[]d</a>e<a href="http://test.test/">f</a></p>',
            stepFunction: unlinkFromPopover,
            contentAfter:
                '<p><a href="http://test.test/">a</a>b<span class="fa fa-music"></span>c[]de<a href="http://test.test/">f</a></p>',
        });
        // With fontawesome at the middle of the link.
        await testEditor({
            contentBefore:
                '<p><a href="http://test.test/">a</a>b<a href="http://test.test/">c<span class="fa fa-music" contenteditable="false">\u200B</span>d[]e</a>f<a href="http://test.test/">g</a></p>',
            stepFunction: unlinkFromPopover,
            contentAfter:
                '<p><a href="http://test.test/">a</a>bc<span class="fa fa-music"></span>d[]ef<a href="http://test.test/">g</a></p>',
        });
        // With fontawesome at the end of the link.
        await testEditor({
            contentBefore:
                '<p><a href="http://test.test/">a</a>b<a href="http://test.test/">c[]d<span class="fa fa-music" contenteditable="false">\u200B</span></a>e<a href="http://test.test/">f</a></p>',
            stepFunction: unlinkFromPopover,
            contentAfter:
                '<p><a href="http://test.test/">a</a>bc[]d<span class="fa fa-music"></span>e<a href="http://test.test/">f</a></p>',
        });
    });
});

describe("range not collapsed", () => {
    describe("remove by toolbar unlink button", () => {
        test("should remove the link in the selected range at the end of a link", async () => {
            // FORWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">bc[d]</a>e</p>',
                stepFunction: unlinkFromToolbar,
                contentAfter: '<p>a<a href="exist">bc</a>[d]e</p>',
            });
        });
        test("should remove fully selected link by toolbar unlink button", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="exist">[bcd]</a>e</p>',
                stepFunction: unlinkFromToolbar,
                contentAfterEdit: "<p>a[bcd]e</p>",
                contentAfter: "<p>a[bcd]e</p>",
            });
        });
        test("should remove fully selected link along with text by toolbar unlink button", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="exist" class="btn btn-primary">[bcd</a>ef]g</p>',
                stepFunction: unlinkFromToolbar,
                contentAfterEdit: "<p>a[bcdef]g</p>",
                contentAfter: "<p>a[bcdef]g</p>",
            });
        });
        test("should remove fully selected link along with text by toolbar unlink button (2)", async () => {
            await testEditor({
                contentBefore: '<p>a[bc<a href="exist">def]</a>g</p>',
                stepFunction: unlinkFromToolbar,
                contentAfterEdit: "<p>a[bcdef]g</p>",
                contentAfter: "<p>a[bcdef]g</p>",
            });
        });
        test("should remove fully selected formatted link by toolbar unlink button", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="exist"><i>[bcd]</i></a>e</p>',
                stepFunction: unlinkFromToolbar,
                contentAfterEdit: "<p>a<i>[bcd]</i>e</p>",
                contentAfter: "<p>a<i>[bcd]</i>e</p>",
            });
        });
    });
    describe("remove by command", () => {
        test("should remove the link in the selected range at the end of a link", async () => {
            // FORWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">bc[d]</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfterEdit: '<p>a\ufeff<a href="exist">\ufeffbc\ufeff</a>\ufeff[d]e</p>',
                contentAfter: '<p>a<a href="exist">bc</a>[d]e</p>',
            });
            // BACKWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">bc]d[</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfterEdit: '<p>a\ufeff<a href="exist">\ufeffbc\ufeff</a>\ufeff]d[e</p>',
                contentAfter: '<p>a<a href="exist">bc</a>]d[e</p>',
            });
        });

        test("should remove the link in the selected range in the middle of a link", async () => {
            // FORWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">b[c]d</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfter: '<p>a<a href="exist">b</a>[c]<a href="exist">d</a>e</p>',
            });
            // BACKWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">b]c[d</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfter: '<p>a<a href="exist">b</a>]c[<a href="exist">d</a>e</p>',
            });
        });

        test("should remove the link in the selected range at the start of a link", async () => {
            // FORWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">[b]cd</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfterEdit: '<p>a[b]\ufeff<a href="exist">\ufeffcd\ufeff</a>\ufeffe</p>',
                contentAfter: '<p>a[b]<a href="exist">cd</a>e</p>',
            });
            // BACKWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">]b[cd</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfterEdit: '<p>a]b[\ufeff<a href="exist">\ufeffcd\ufeff</a>\ufeffe</p>',
                contentAfter: '<p>a]b[<a href="exist">cd</a>e</p>',
            });
        });

        test("should remove the link in the selected range overlapping the end of a link", async () => {
            // FORWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">bc[d</a>e]f</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfter: '<p>a<a href="exist">bc</a>[de]f</p>',
            });
            // BACKWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">bc]d</a>e[f</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfter: '<p>a<a href="exist">bc</a>]de[f</p>',
            });
        });

        test("should remove the link in the selected range overlapping the start of a link", async () => {
            // FORWARD
            await testEditor({
                contentBefore: '<p>a[b<a href="exist">c]de</a>f</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfter: '<p>a[bc]<a href="exist">de</a>f</p>',
            });
            // BACKWARD
            await testEditor({
                contentBefore: '<p>a]b<a href="exist">c[de</a>f</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfter: '<p>a]bc[<a href="exist">de</a>f</p>',
            });
        });

        test("should not unlink selected non-editable links", async () => {
            await testEditor({
                contentBefore:
                    '<p><a href="exist">[ab</a><a contenteditable="false" href="exist">cd</a>ef]</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfter: '<p>[ab<a contenteditable="false" href="exist">cd</a>ef]</p>',
            });
        });

        test("should not unlink editable links with selection in non-editable", async () => {
            await testEditor({
                contentBefore:
                    '<p contenteditable="false">ab<a contenteditable="true" href="http://test.test">[cd]</a>ef</p>',
                stepFunction: unlinkByCommand,
                contentAfter:
                    '<p contenteditable="false">ab<a contenteditable="true" href="http://test.test">[cd]</a>ef</p>',
            });
        });

        test("should not remove unremovable links when inside selection with other links", async () => {
            await testEditor({
                contentBefore:
                    '<p>[a<a href="http://test.test">b</a>c<a class="oe_unremovable" href="http://test.test">d</a>e<a href="http://test.test">f]</a></p>',
                stepFunction: unlinkByCommand,
                contentAfter:
                    '<p>[abc<a class="oe_unremovable" href="http://test.test">d</a>ef]</p>',
            });
        });

        test("should not remove selected part of unremovable links when partially selected with other links", async () => {
            await testEditor({
                contentBefore:
                    '<p><a class="oe_unremovable" href="http://test.test">a[b</a>c<a href="http://test.test">d</a>e<a class="oe_unremovable" href="http://test.test">f]g</a></p>',
                stepFunction: unlinkByCommand,
                contentAfter:
                    '<p><a class="oe_unremovable" href="http://test.test">a[b</a>cde<a class="oe_unremovable" href="http://test.test">f]g</a></p>',
            });
        });
        test("should not remove unremovable links when fully selected with other links", async () => {
            await testEditor({
                contentBefore:
                    '<p>a<a class="oe_unremovable" href="http://test.test">[b</a>c<a href="http://test.test">d</a>e<a class="oe_unremovable" href="http://test.test">f]</a></p>',
                stepFunction: unlinkByCommand,
                contentAfter:
                    '<p>a<a class="oe_unremovable" href="http://test.test">[b</a>cde<a class="oe_unremovable" href="http://test.test">f]</a></p>',
            });
        });
        test("should not remove unremovable links when fully selected (including feff) with other links", async () => {
            await testEditor({
                contentBefore:
                    '<p>a<a class="oe_unremovable" href="http://test.test">[b</a>c<a href="http://test.test">d</a>e<a class="oe_unremovable" href="http://test.test">f]</a></p>',
                /** @param {import("@html_editor/plugin").Editor} editor */
                stepFunction: (editor) => {
                    const selection = editor.shared.selection.getEditableSelection();
                    // extends selection to contain the feffs
                    editor.shared.selection.setSelection({
                        anchorNode: selection.anchorNode.previousSibling,
                        anchorOffset: 0,
                        focusNode: selection.focusNode.nextSibling,
                        focusOffset: 1,
                    });
                    unlinkByCommand(editor);
                },
                contentAfter:
                    '<p>a<a class="oe_unremovable" href="http://test.test">[b</a>cde<a class="oe_unremovable" href="http://test.test">f]</a></p>',
            });
        });
    });
    test("should be able to remove link if selection has FEFF character", async () => {
        const { el } = await setupEditor(
            '<p><a href="google.com" class="btn btn-primary">[test]</a></p>'
        );
        const link = el.querySelector("a");
        const firstFeffChar = link.firstChild;
        const secondFeffChar = link.lastChild;
        setSelection({
            anchorNode: firstFeffChar,
            anchorOffset: 0,
            focusNode: secondFeffChar,
            focusOffset: 1,
        });
        await unlinkFromToolbar();
        expect(getContent(el)).toBe("<p>[test]</p>");
    });
    test("should be able to remove link if selection has FEFF character (2)", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.test/" class="btn btn-primary">[]test</a></p>'
        );
        const link = el.querySelector("a");
        const firstFeffChar = link.firstChild;
        const textNode = firstFeffChar.nextSibling;
        const secondFeffChar = link.lastChild;
        setSelection({
            anchorNode: secondFeffChar,
            anchorOffset: 1,
            focusNode: textNode,
            focusOffset: 0,
        });
        await unlinkFromToolbar();
        expect(getContent(el)).toBe("<p>]test[</p>");
    });
});

describe("empty link", () => {
    test("should not remove empty link in uneditable zone", async () => {
        await testEditor({
            contentBefore: '<p contenteditable="false"><a href="exist"></a></p>',
            contentAfter: '<p contenteditable="false"><a href="exist"></a></p>',
        });
    });
    test("should not remove empty link in uneditable zone (2)", async () => {
        await testEditor({
            contentBefore:
                '<p>[]<span contenteditable="false"><a contenteditable="true" href="exist"></a></span></p>',
            contentAfter:
                '<p>[]<span contenteditable="false"><a contenteditable="true" href="exist"></a></span></p>',
        });
    });
});
