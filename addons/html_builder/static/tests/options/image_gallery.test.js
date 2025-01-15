import { expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../helpers";
import { animationFrame, click, queryAll, waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

test("Add image in gallery", async () => {
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", (test) => {
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
    await setupWebsiteBuilder(
        `
        <section class="s_image_gallery o_masonry" data-columns="2">
            <div class="container">
                <div class="o_masonry_col col-lg-6">
                    <img class="first_img img img-fluid d-block rounded" data-index="1" src='${base64Img}'>
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="2" src='${base64Img}'>
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="3" src='${base64Img}'>
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="4" src='${base64Img}'>
                </div>
                <div class="o_masonry_col col-lg-6">
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="5"  src='${base64Img}'>
                </div>
            </div>
        </section>
        `,
        { loadIframeBundles: true }
    );
    await contains(":iframe .first_img").click();
    expect("[data-action-id='addImage']").toHaveCount(1);
    await click("[data-action-id='addImage']");
    await animationFrame();
    await click("img.o_we_attachment_highlight");
    await animationFrame();
    await click(".modal-footer button");
    await waitFor(":iframe img[data-index='6']");

    const columns = queryAll(":iframe .o_masonry_col");
    const columnImgs = columns.map((column) =>
        [...column.children].map((img) => img.dataset.index)
    );

    expect(columnImgs).toEqual([["1", "3", "4", "5", "6"], ["2"]]);
});
