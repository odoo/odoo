import { describe, test } from "@odoo/hoot";
import { deleteBackward, insertLineBreak, insertText, undo } from "../_helpers/user_actions";
import { testEditor } from "../_helpers/editor";
import { animationFrame } from "@odoo/hoot-mock";

describe("range collapsed", () => {
    test("should not change the url when a link is not edited", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="https://google.co">google.com</a>b</p>',
            contentAfter: '<p>a<a href="https://google.co">google.com</a>b</p>',
        });
        await testEditor({
            contentBefore:
                '<p>a<a href="https://google.xx">google.com</a>b<a href="https://google.co">cd[]</a></p>',
            stepFunction: async (editor) => {
                await insertText(editor, "e");
            },
            contentAfter:
                '<p>a<a href="https://google.xx">google.com</a>b<a href="https://google.co">cde[]</a></p>',
        });
    });

    test("should change the url when the label change", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "m");
            },
            contentAfter: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="https://gogle.com">go[]gle.com</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "o");
            },
            contentAfter: '<p>a<a href="https://google.com">goo[]gle.com</a>b</p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="https://else.com">go[]gle.com</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "o");
            },
            contentAfter: '<p>a<a href="https://else.com">goo[]gle.com</a>b</p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="https://else.com">http://go[]gle.com</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "o");
            },
            contentAfter: '<p>a<a href="https://else.com">http://goo[]gle.com</a>b</p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="mailto:hello@moto.com">hello@moto[].com</a></p>',
            stepFunction: async (editor) => {
                await insertText(editor, "r");
            },
            contentAfter: '<p>a<a href="mailto:hello@motor.com">hello@motor[].com</a></p>',
        });
    });

    test("should change the url when the label change, without changing the protocol", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="http://google.co">google.co[]</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "m");
            },
            contentAfter: '<p>a<a href="http://google.com">google.com[]</a>b</p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "m");
            },
            contentAfter: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
        });
    });

    test("should change the url when the label change, changing to the suitable protocol", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="http://hellomoto.com">hello[]moto.com</a></p>',
            stepFunction: async (editor) => {
                await insertText(editor, "@");
            },
            contentAfter: '<p>a<a href="mailto:hello@moto.com">hello@[]moto.com</a></p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="mailto:hello@moto.com">hello@[]moto.com</a></p>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfter: '<p>a<a href="https://hellomoto.com">hello[]moto.com</a></p>',
        });
    });

    test("should change the url in one step", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "m");
                await undo(editor);
            },
            contentAfter: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
        });
    });

    test("should not change the url when the label change (1)", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "u");
            },
            contentAfter: '<p>a<a href="https://google.com">google.comu[]</a>b</p>',
        });
    });

    test("should not change the url when the label change (2)", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
            stepFunction: async (editor) => {
                await animationFrame();
                await insertLineBreak(editor);
                await insertText(editor, "odoo.com");
            },
            contentAfter: '<p>a<a href="https://google.com">google.com</a><br>odoo.com[]b</p>',
        });
    });
});

describe("range not collapsed", () => {
    test("should change the url when the label change", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="https://google.com">google.[com]</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "be");
            },
            contentAfter: '<p>a<a href="https://google.be">google.be[]</a>b</p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="https://gogle.com">[yahoo].com</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "google");
            },
            contentAfter: '<p>a<a href="https://gogle.com">google[].com</a>b</p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="https://else.com">go[gle.c]om</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, ".c");
            },
            contentAfter: '<p>a<a href="https://else.com">go.c[]om</a>b</p>',
        });
    });

    test("should not change the url when the label change", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="https://google.com">googl[e.com]</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "e");
            },
            contentAfter: '<p>a<a href="https://google.com">google[]</a>b</p>',
        });
        await testEditor({
            contentBefore: '<p>a<a href="https://google.com">google.[com]</a>b</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "vvv");
            },
            contentAfter: '<p>a<a href="https://google.com">google.vvv[]</a>b</p>',
        });
    });
});
