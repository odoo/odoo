import { expect, test } from "@odoo/hoot";
import { click, getActiveElement, press, queryOne, waitFor } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { makeMockEnv, onRpc } from "@web/../tests/web_test_helpers";
import { getContent } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";

test("Can replace an image", async () => {
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
    await setupEditor(`<p> <img class="img-fluid" src="/web/static/img/logo.png"> </p>`, { env });
    expect("img[src='/web/static/img/logo.png']").toHaveCount(1);
    click("img");
    await tick(); // selectionchange
    await waitFor(".o-we-toolbar");
    expect("button[name='replace_image']").toHaveCount(1);
    click("button[name='replace_image']");
    await animationFrame();
    click("img.o_we_attachment_highlight");
    await animationFrame();
    expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
    expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);
});

test("Selection is collapsed after the image after replacing it", async () => {
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
    const { el } = await setupEditor(
        `<p>abc<img class="img-fluid" src="/web/static/img/logo.png">def</p>`,
        { env }
    );
    click("img");
    await waitFor(".o-we-toolbar");
    expect("button[name='replace_image']").toHaveCount(1);
    click("button[name='replace_image']");
    await animationFrame();
    click("img.o_we_attachment_highlight");
    await animationFrame();
    expect(getContent(el).replace(/<img.*?>/, "<img>")).toBe("<p>abc<img>[]def</p>");
});

test("Can insert an image, and selection should be collapsed after it", async () => {
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
    const { editor, el } = await setupEditor("<p>a[]bc</p>", { env });
    insertText(editor, "/image");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    press("Enter");
    await animationFrame();
    click("img.o_we_attachment_highlight");
    await animationFrame();
    expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);
    expect(getContent(el).replace(/<img.*?>/, "<img>")).toBe("<p>a<img>[]bc</p>");
});

test("press escape to close media dialog", async () => {
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => {
        return [];
    });
    const env = await makeMockEnv();
    const { editor, el } = await setupEditor("<p>a[]bc</p>", { env });
    insertText(editor, "/image");
    await waitFor(".o-we-powerbox");
    press("Enter");
    await animationFrame();
    expect(getActiveElement()).toBe(queryOne(".modal .o_select_media_dialog .o_we_search"));

    press("escape");
    await animationFrame();
    expect(".modal .o_select_media_dialog").toHaveCount(0);
    expect(getContent(el)).toBe("<p>a[]bc</p>");
});
