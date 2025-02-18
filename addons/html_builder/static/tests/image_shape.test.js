import { before, expect, globals, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

const testImg = `<img data-original-id="1" data-mimetype="image/png" src='/web/image/website.s_text_image_default_image'>`;

function onRpcReal(route) {
    onRpc(route, async () => globals.fetch.call(window, route), { pure: true });
}
before(() => {
    onRpc("/html_editor/get_image_info", async (data) => ({
        attachment: {
            id: 1,
        },
        original: {
            id: 1,
            image_src: "/website/static/src/img/snippets_demo/s_text_image.jpg",
            mimetype: "image/jpeg",
        },
    }));
    onRpcReal("/html_builder/static/image_shapes/geometric/geo_shuriken.svg");
    onRpcReal("/web/image/website.s_text_image_default_image");
    onRpcReal("/website/static/src/img/snippets_demo/s_text_image.jpg");
});

test("Should set a shape on an image", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});

    const img = queryFirst(":iframe .test-options-target img");
    expect(":iframe .test-options-target img").toHaveAttribute("data-original-id", "1");
    expect(":iframe .test-options-target img").toHaveAttribute("data-mimetype", "image/png");
    expect(img.src.startsWith("data:image/svg+xml;base64,")).toBe(true);
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-original-src",
        "/website/static/src/img/snippets_demo/s_text_image.jpg"
    );
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-mimetype-before-conversion",
        "image/jpeg"
    );
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-shape",
        "html_builder/geometric/geo_shuriken"
    );
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-file-name",
        "s_text_image.svg"
    );
    expect(":iframe .test-options-target img").toHaveAttribute("data-shape-colors", ";;;;");
});
