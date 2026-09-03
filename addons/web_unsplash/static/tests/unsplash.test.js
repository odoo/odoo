import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expectElementCount } from "@html_editor/../tests/_helpers/ui_expectations";
import { expect, test } from "@odoo/hoot";
import { animationFrame, click, press, waitFor } from "@odoo/hoot-dom";
import { contains, makeMockEnv, onRpc, mountWithCleanup, defineModels, models } from "@web/../tests/web_test_helpers";
import { CustomMediaDialog } from "@html_editor/fields/x2many_field/custom_media_dialog";

test("Unsplash is inserted in the Media Dialog", async () => {
    const imageRecord = {
        id: 1,
        name: "logo",
        mimetype: "image/png",
        image_src: "/web/static/img/logo2.png",
        access_token: false,
        public: true,
    };
    onRpc("ir.attachment", "search_read", () => [imageRecord]);
    const fetchDef = Promise.withResolvers();
    onRpc("/web_unsplash/fetch_images", () => {
        expect.step("fetch_images");
        fetchDef.resolve();
        return {
            total: 1,
            total_pages: 1,
            results: [
                {
                    id: "oXV3bzR7jxI",
                    alt_description: "An image alt description",
                    urls: {
                        regular: "/web/static/img/logo2.png",
                    },
                    user: {
                        name: "Username",
                        links: {
                            html: "https://example.com/",
                        },
                    },
                    links: {
                        download_location: "https://example.com/",
                    },
                },
            ],
        };
    });
    onRpc("/web_unsplash/attachment/add", (args) => [
        { ...imageRecord, description: "unsplash_image" },
    ]);
    const env = await makeMockEnv();
    const { editor } = await setupEditor(`<p>[]</p>`, { env });
    await expectElementCount(".o-we-powerbox", 0);
    await insertText(editor, "/image");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);
    await click(".o-we-command");
    await animationFrame();
    expect(".o_select_media_dialog").toHaveCount(1);
    contains("input.o_we_search").edit("cat");
    await fetchDef.promise;
    expect.verifySteps(["fetch_images"]);
    await waitFor("img[title='Username']");
    await click(".o_button_area[aria-label='Username']");
    await waitFor(".o-wysiwyg img[alt='unsplash_image']");
    expect(".o-wysiwyg img[alt='unsplash_image']").toHaveCount(1);
});

test("Unsplash images are processed correctly in CustomMediaDialog", async () => {
    class IrAttachment extends models.Model {
        _name = "ir.attachment";
    }
    defineModels([IrAttachment]);

    const fetchDef = Promise.withResolvers();
    onRpc("/web_unsplash/fetch_images", () => {
        fetchDef.resolve();
        return {
            total: 1,
            total_pages: 1,
            results: [{
                id: "unsplash123",
                urls: { regular: "/web/static/img/logo2.png" },
                user: { name: "Logo", links: { html: "" } },
                links: { download_location: "" },
            }],
        }
    });
    onRpc("/html_editor/media_library_search", () => {
        return { media: [], results: null };
    });
    onRpc("/web_unsplash/attachment/add", async (request) => {
        const { params } = await request.json();
        expect(params.res_model).toBe("product.product");
        return [{ id: 99, mimetype: "image/png", image_src: "/web/static/img/logo2.png" }];
    });
    onRpc("ir.attachment", "search_read", () => []);
    onRpc("ir.attachment", "generate_access_token", () => ["12345"]);

    let savePayload;
    const env = await makeMockEnv();
    env.dialogData = { close: () => {}, isActive: true, scrollToOrigin: () => {} },
    await mountWithCleanup(CustomMediaDialog, {
        env,
        props: {
            resModel: "product.product",
            resId: 1,
            close: () => {},
            save: () => {},
            imageSave: (attachments) => { savePayload = attachments; },
            document: document,
        },
    });
    contains("input.o_we_search").edit("Logo");
    await fetchDef.promise;
    await waitFor("img[title='Logo']");
    await click(".o_button_area[aria-label='Logo']");
    await click(".o_select_media_dialog .btn-primary");
    expect(savePayload).toEqual([{ id: 99 }]);
});

test("Unsplash error is displayed when there is no key", async () => {
    const imageRecord = {
        id: 1,
        name: "logo",
        mimetype: "image/png",
        image_src: "/web/static/img/logo2.png",
        access_token: false,
        public: true,
    };
    onRpc("ir.attachment", "search_read", () => [imageRecord]);
    const fetchDef = Promise.withResolvers();
    onRpc("/web_unsplash/fetch_images", () => {
        fetchDef.resolve();
        return {
            error: "key_not_found",
        };
    });
    const env = await makeMockEnv();
    const { editor } = await setupEditor(`<p>[]</p>`, { env });
    await expectElementCount(".o-we-powerbox", 0);
    await insertText(editor, "/image");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);
    await click(".o-we-command");
    await animationFrame();
    expect(".o_select_media_dialog").toHaveCount(1);
    contains("input.o_we_search").edit("cat");
    await fetchDef.promise;
    await waitFor(".unsplash_error");
    expect(".unsplash_error").toHaveCount(1);
});

test("Document tab does not crash with FileSelector extension", async () => {
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
    const { editor } = await setupEditor("<p>a[]</p>", { env });
    await insertText(editor, "/image");
    await animationFrame();
    await press("enter");
    await animationFrame();
    await click("li:nth-child(2) > button.nav-link");
    expect(".o_existing_attachment_cell").toHaveCount(1);
});
