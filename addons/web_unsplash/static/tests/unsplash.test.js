import { expect, test } from "@odoo/hoot";
import { click, waitFor, press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, makeMockEnv, onRpc } from "@web/../tests/web_test_helpers";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { Deferred } from "@web/../lib/hoot/hoot-mock";

test("Unsplash is inserted in the Media Dialog", async () => {
    const imageRecord = {
        id: 1,
        name: "logo",
        mimetype: "image/png",
        image_src: "/web/static/img/logo2.png",
        access_token: false,
        public: true,
    };
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => {
        return [imageRecord];
    });
    const fetchDef = new Deferred();
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
    onRpc("/web_unsplash/attachment/add", (args) => {
        return [{ ...imageRecord, description: "unsplash_image" }];
    });
    const env = await makeMockEnv();
    const { editor } = await setupEditor(`<p>[]</p>`, { env });
    expect(".o-we-powerbox").toHaveCount(0);
    await insertText(editor, "/image");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    await click(".o-we-command");
    await animationFrame();
    expect(".o_select_media_dialog").toHaveCount(1);
    contains("input.o_we_search").edit("cat");
    await fetchDef;
    expect.verifySteps(["fetch_images"]);
    await waitFor("img[title='Username']");
    await click("img[title='Username']");
    await waitFor(".o-wysiwyg img[alt='unsplash_image']");
    expect(".o-wysiwyg img[alt='unsplash_image']").toHaveCount(1);
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
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => {
        return [imageRecord];
    });
    const fetchDef = new Deferred();
    onRpc("/web_unsplash/fetch_images", () => {
        fetchDef.resolve();
        return {
            error: "key_not_found",
        };
    });
    const env = await makeMockEnv();
    const { editor } = await setupEditor(`<p>[]</p>`, { env });
    expect(".o-we-powerbox").toHaveCount(0);
    await insertText(editor, "/image");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    await click(".o-we-command");
    await animationFrame();
    expect(".o_select_media_dialog").toHaveCount(1);
    contains("input.o_we_search").edit("cat");
    await fetchDef;
    await waitFor(".unsplash_error");
    expect(".unsplash_error").toHaveCount(1);
});

test("Document tab does not crash with FileSelector extension", async () => {
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => {
        return [
            {
                id: 1,
                name: "logo",
                mimetype: "image/png",
                image_src: "/web/static/img/logo2.png",
                access_token: false,
                public: true,
            },
        ];
    });
    const env = await makeMockEnv();
    const { editor } = await setupEditor("<p>a[]</p>", { env });
    await insertText(editor, "/image");
    await animationFrame();
    await press("enter");
    await animationFrame();
    await click("li:nth-child(2) > a.nav-link");
    expect(".o_existing_attachment_cell").toHaveCount(1);
});
