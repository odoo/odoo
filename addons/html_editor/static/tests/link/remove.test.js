import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unlinkFromPopover, unlinkByCommand, unlinkFromToolbar } from "../_helpers/user_actions";

describe("range collapsed, remove by popover unlink button", () => {
    test("should remove the link if collapsed range at the end of a link", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="exist">bcd[]</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: "<p>abcd[]e</p>",
        });
        // With fontawesome at the start of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist"><span class="fa fa-music" contenteditable="false">\u200B</span>bcd[]</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a<span class="fa fa-music"></span>bcd[]e</p>',
        });
        // With fontawesome at the middle of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist">bc<span class="fa fa-music" contenteditable="false">\u200B</span>d[]</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>abc<span class="fa fa-music"></span>d[]e</p>',
        });
        // With fontawesome at the end of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist">bcd[]<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>abcd[]<span class="fa fa-music"></span>e</p>',
        });
    });

    test("should remove the link if collapsed range in the middle a link", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="exist">b[]cd</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: "<p>ab[]cde</p>",
        });
        // With fontawesome at the start of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist"><span class="fa fa-music" contenteditable="false">\u200B</span>b[]cd</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a<span class="fa fa-music"></span>b[]cde</p>',
        });
        // With fontawesome at the middle of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist">b[]c<span class="fa fa-music" contenteditable="false">\u200B</span>d</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>ab[]c<span class="fa fa-music"></span>de</p>',
        });
        // With fontawesome at the end of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist">b[]cd<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>ab[]cd<span class="fa fa-music"></span>e</p>',
        });
    });

    test("should remove the link if collapsed range at the start of a link", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="exist">[]bcd</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: "<p>a[]bcde</p>",
        });
        // With fontawesome at the start of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist"><span class="fa fa-music" contenteditable="false">\u200B</span>[]bcd</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a<span class="fa fa-music"></span>[]bcde</p>',
        });
        // With fontawesome at the middle of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist">[]bc<span class="fa fa-music" contenteditable="false">\u200B</span>d</a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a[]bc<span class="fa fa-music"></span>de</p>',
        });
        // With fontawesome at the end of the link.
        await testEditor({
            contentBefore:
                '<p>a<a href="exist">[]bcd<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p>a[]bcd<span class="fa fa-music"></span>e</p>',
        });
    });

    test("should remove only the current link if collapsed range in the middle of a link", async () => {
        await testEditor({
            contentBefore:
                '<p><a href="exist">a</a>b<a href="exist">c[]d</a>e<a href="exist">f</a></p>',
            stepFunction: unlinkFromPopover,
            contentAfter: '<p><a href="exist">a</a>bc[]de<a href="exist">f</a></p>',
        });
        // With fontawesome at the start of the link.
        await testEditor({
            contentBefore:
                '<p><a href="exist">a</a>b<a href="exist"><span class="fa fa-music" contenteditable="false">\u200B</span>c[]d</a>e<a href="exist">f</a></p>',
            stepFunction: unlinkFromPopover,
            contentAfter:
                '<p><a href="exist">a</a>b<span class="fa fa-music"></span>c[]de<a href="exist">f</a></p>',
        });
        // With fontawesome at the middle of the link.
        await testEditor({
            contentBefore:
                '<p><a href="exist">a</a>b<a href="exist">c<span class="fa fa-music" contenteditable="false">\u200B</span>d[]e</a>f<a href="exist">g</a></p>',
            stepFunction: unlinkFromPopover,
            contentAfter:
                '<p><a href="exist">a</a>bc<span class="fa fa-music"></span>d[]ef<a href="exist">g</a></p>',
        });
        // With fontawesome at the end of the link.
        await testEditor({
            contentBefore:
                '<p><a href="exist">a</a>b<a href="exist">c[]d<span class="fa fa-music" contenteditable="false">\u200B</span></a>e<a href="exist">f</a></p>',
            stepFunction: unlinkFromPopover,
            contentAfter:
                '<p><a href="exist">a</a>bc[]d<span class="fa fa-music"></span>e<a href="exist">f</a></p>',
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
    });
    describe("remove by command", () => {
        test("should remove the link in the selected range at the end of a link", async () => {
            // FORWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">bc[d]</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
                contentAfter: '<p>a<a href="exist">bc</a>[d]e</p>',
            });
            // BACKWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">bc]d[</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
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
                contentAfter: '<p>a[b]<a href="exist">cd</a>e</p>',
            });
            // BACKWARD
            await testEditor({
                contentBefore: '<p>a<a href="exist">]b[cd</a>e</p>',
                stepFunction: async (editor) => {
                    await unlinkByCommand(editor);
                },
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
