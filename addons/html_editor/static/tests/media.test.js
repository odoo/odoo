import { EDITABLE_MEDIA_CLASS } from "@html_editor/utils/dom_info";
import { describe, expect, test } from "@odoo/hoot";
import { click, press, waitFor } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { makeMockEnv, onRpc } from "@web/../tests/web_test_helpers";
import { cleanHints } from "./_helpers/dispatch";
import { base64Img, setupEditor, testEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { expectElementCount } from "./_helpers/ui_expectations";
import { deleteBackward, deleteForward, insertText } from "./_helpers/user_actions";
import { MAIN_PLUGINS, NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS } from "@html_editor/plugin_sets";

test("Can replace an image", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    const env = await makeMockEnv();
    await setupEditor(`<p> <img class="img-fluid" src="/web/static/img/logo.png"> </p>`, { env });
    expect("img[src='/web/static/img/logo.png']").toHaveCount(1);
    await click("img");
    await tick(); // selectionchange
    await waitFor(".o-we-toolbar");
    expect("button[name='replace_image']").toHaveCount(1);
    await click("button[name='replace_image']");
    await animationFrame();
    await click("img.o_we_attachment_highlight");
    await animationFrame();
    expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
    expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);
});

test("Replace an image with link by a document should remove the link", async () => {
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => [
        {
            id: 1,
            name: "file.txt",
            mimetype: "text/plain",
            public: true,
            image_src: "",
        },
    ]);
    const env = await makeMockEnv();
    await setupEditor(
        `<p><a href="http://test.com"><img class="img-fluid" src="/web/static/img/logo.png"></a></p>`,
        { env, config: { Plugins: [...MAIN_PLUGINS, ...NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS] } }
    );
    expect("img[src='/web/static/img/logo.png']").toHaveCount(1);
    await click("img");
    await tick(); // selectionchange
    await waitFor(".o-we-toolbar");
    expect("button[name='replace_image']").toHaveCount(1);
    await click("button[name='replace_image']");
    await animationFrame();
    await click(".nav-link:contains('Documents')");
    await animationFrame();
    await click(".o_we_attachment_highlight");
    expect(".odoo-editor-editable .o_file_box a:contains('file.txt')").toHaveCount(1);
    expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
    expect("p a[href='http://test.com']").toHaveCount(0);
});

test.tags("focus required");
test("Selection is collapsed after the image after replacing it", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    const env = await makeMockEnv();
    const { el } = await setupEditor(
        `<p>abc<img class="img-fluid" src="/web/static/img/logo.png">def</p>`,
        { env }
    );
    await click("img");
    await waitFor(".o-we-toolbar");
    expect("button[name='replace_image']").toHaveCount(1);
    await click("button[name='replace_image']");
    await animationFrame();
    await click("img.o_we_attachment_highlight");
    await animationFrame();
    expect(getContent(el).replace(/<img.*?>/, "<img>")).toBe("<p>abc<img>[]def</p>");
});

test.tags("focus required");
test("Can insert an image, and selection should be collapsed after it", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    const env = await makeMockEnv();
    const { editor, el } = await setupEditor("<p>a[]bc</p>", { env });
    await insertText(editor, "/image");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);
    await press("Enter");
    await animationFrame();
    await click("img.o_we_attachment_highlight");
    await animationFrame();
    expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);
    expect(getContent(el).replace(/<img.*?>/, "<img>")).toBe("<p>a<img>[]bc</p>");
});

test("press escape to close media dialog", async () => {
    onRpc("ir.attachment", "search_read", () => []);
    const env = await makeMockEnv();
    const { editor, el } = await setupEditor("<p>a[]bc</p>", { env });
    await insertText(editor, "/image");
    await waitFor(".o-we-powerbox");
    await press("Enter");
    await animationFrame();
    expect(".modal .o_select_media_dialog .o_we_search").toBeFocused();

    await press("escape");
    await animationFrame();
    expect(".modal .o_select_media_dialog").toHaveCount(0);
    expect(getContent(el)).toBe("<p>a[]bc</p>");
});

describe("Powerbox search keywords", () => {
    test("Image and Icon are keywords for the Media command", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>");
        await insertText(editor, "/");
        for (const word of ["image", "icon"]) {
            await insertText(editor, word);
            await animationFrame();
            expect(".active .o-we-command-name").toHaveText("Media");
            // delete the keyword to try the next one
            for (let i = 0; i < word.length; i++) {
                await press("backspace");
            }
        }
    });
});

describe("(non-)editable media", () => {
    describe.tags("desktop");
    describe("toolbar", () => {
        test("toolbar should open when clicking on an image in an editable context", async () => {
            const { editor } = await setupEditor(
                `<div contenteditable="true"><img src="${base64Img}"></div>`
            );
            await click("img");
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 1);
            // Now pressing the delete button should remove the image.
            await click(".o-we-toolbar button[name='image_delete']");
            cleanHints(editor);
            expect(getContent(editor.editable)).toBe(
                `<div contenteditable="true" class="o-paragraph">[]<br></div>`
            );
        });
        test("toolbar should not open when clicking on an image in an non-editable context", async () => {
            const { editor } = await setupEditor(
                `<div contenteditable="false"><img src="${base64Img}"></div>`
            );
            await click("img");
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);
            expect(getContent(editor.editable)).toBe(
                `<div contenteditable="false">[<img src="${base64Img}">]</div>`
            );
        });
        test("toolbar should open when clicking on an editable image in a non-editable context", async () => {
            const { editor } = await setupEditor(
                `<div contenteditable="false"><img src="${base64Img}" class="${EDITABLE_MEDIA_CLASS}"></div>`
            );
            await click("img");
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 1);
            // Now pressing the delete button should remove the image.
            await click(".o-we-toolbar button[name='image_delete']");
            expect(getContent(editor.editable)).toBe(`<div contenteditable="false">[]<br></div>`);
        });
    });
    describe("delete", () => {
        test("delete should remove an image in an editable context", async () => {
            const contentBefore = `<div contenteditable="true"><img src="${base64Img}"></div>`;
            const contentAfter = `<div contenteditable="true">[]<br></div>`;
            // Forward
            await testEditor({
                contentBefore,
                stepFunction: async (editor) => {
                    await click("img");
                    deleteForward(editor);
                },
                contentAfter,
            });
            // Backward
            await testEditor({
                contentBefore,
                stepFunction: async (editor) => {
                    await click("img");
                    deleteBackward(editor);
                },
                contentAfter,
            });
        });
        test("delete should not remove an image in an non-editable context", async () => {
            const contentBefore = `<div contenteditable="false"><img src="${base64Img}"></div>`;
            // Forward
            await testEditor({
                contentBefore,
                stepFunction: async (editor) => {
                    await click("img");
                    deleteForward(editor);
                },
                // TODO: there should be no difference between forward and backward.
                contentAfter: `<div contenteditable="false">[<img src="${base64Img}">]</div>`,
            });
            // Backward
            await testEditor({
                contentBefore,
                stepFunction: async (editor) => {
                    await click("img");
                    deleteBackward(editor);
                },
                // TODO: there should be no difference between forward and backward.
                contentAfter: `<div contenteditable="false">[]<img src="${base64Img}"></div>`,
            });
        });
        test("delete should remove an editable image in a non-editable context", async () => {
            const contentBefore = `<div contenteditable="false"><img src="${base64Img}" class="${EDITABLE_MEDIA_CLASS}"></div>`;
            const contentAfter = `<div contenteditable="false">[]<br></div>`;
            // Forward
            await testEditor({
                contentBefore,
                stepFunction: async (editor) => {
                    await click("img");
                    deleteForward(editor);
                },
                contentAfter,
            });
            // Backward
            await testEditor({
                contentBefore,
                stepFunction: async (editor) => {
                    await click("img");
                    deleteBackward(editor);
                },
                contentAfter,
            });
        });
    });
});

test("cropper should not open for external image", async () => {
    onRpc("/html_editor/get_image_info", () => ({
        original: false,
    }));

    await setupEditor(
        `<p>[<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">]</p>`
    );
    await waitFor('button[name="image_transform"]');

    await click('button[name="image_transform"]');
    await animationFrame();

    await click('.btn[name="image_crop"]');
    await waitFor(".o_notification_manager .o_notification", { timeout: 1000 });
    expect("img.o_we_cropper_img").toHaveCount(0);
});
