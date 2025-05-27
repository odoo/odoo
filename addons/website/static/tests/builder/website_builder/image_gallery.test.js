import { expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains, dataURItoBlob, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, dummyBase64Img, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

test("Add image in gallery", async () => {
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/image/hoot.png",
            access_token: false,
            public: true,
        },
    ]);

    onRpc(
        "/web/image/hoot.png",
        () => {
            const base64Image =
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=";
            return dataURItoBlob(base64Image);
        },
        { pure: true }
    );

    await setupWebsiteBuilder(
        `
        <section class="s_image_gallery o_masonry" data-columns="2">
            <div class="container">
                <div class="o_masonry_col col-lg-6">
                    <img class="first_img img img-fluid d-block rounded" data-index="1" src='${dummyBase64Img}'>
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="2" src='${dummyBase64Img}'>
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="3" src='${dummyBase64Img}'>
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="4" src='${dummyBase64Img}'>
                </div>
                <div class="o_masonry_col col-lg-6">
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="5"  src='${dummyBase64Img}'>
                </div>
            </div>
        </section>
        `
    );
    onRpc("/html_editor/get_image_info", () => {
        expect.step("get_image_info");
        return {
            attachment: {
                id: 1,
            },
            original: {
                id: 1,
                image_src: "/web/image/hoot.png",
                mimetype: "image/png",
            },
        };
    });
    await contains(":iframe .first_img").click();
    await waitFor("[data-action-id='addImage']");
    expect("[data-action-id='addImage']").toHaveCount(1);
    await contains("[data-action-id='addImage']").click();
    // We use "click" instead of contains.click because contains wait for the image to be visible.
    // In this test we don't want to wait ~800ms for the image to be visible but we can still click on it
    await click("img.o_we_attachment_highlight");
    await animationFrame();
    await contains(".modal-footer button").click();
    await waitFor(":iframe .o_masonry_col img[data-index='6']");

    const columns = queryAll(":iframe .o_masonry_col");
    const columnImgs = columns.map((column) =>
        [...column.children].map((img) => img.dataset.index)
    );

    expect(columnImgs).toEqual([["1", "3", "4", "5", "6"], ["2"]]);
    expect.verifySteps([
        "get_image_info",
        "get_image_info",
        "get_image_info",
        "get_image_info",
        "get_image_info",
    ]);
    expect(":iframe .o_masonry_col img[data-index='6']").toHaveAttribute(
        "data-mimetype",
        "image/webp"
    );
    expect(":iframe .o_masonry_col img[data-index='6']").toHaveAttribute(
        "data-mimetype-before-conversion",
        "image/png"
    );
});

// TODO Re-enable once interactions run within iframe in hoot tests.
test.skip("Remove all images in gallery", async () => {
    await setupWebsiteBuilder(
        `
        <section class="s_image_gallery o_masonry" data-columns="2">
            <div class="container">
                <div class="o_masonry_col col-lg-6">
                    <img class="first_img img img-fluid d-block rounded" data-index="1" src='${dummyBase64Img}'>
                </div>
                <div class="o_masonry_col col-lg-6">
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="5"  src='${dummyBase64Img}'>
                </div>
            </div>
        </section>
        `
    );
    await contains(":iframe .first_img").click();
    expect("[data-action-id='removeAllImages']").toHaveCount(1);
    await contains("[data-action-id='removeAllImages']").click();

    expect(":iframe .s_image_gallery img").toHaveCount(0);
    expect(":iframe .o_add_images").toHaveCount(1);
    await contains(":iframe .o_add_images").click();
    expect(".o_select_media_dialog").toHaveCount(1);
});

test("Change gallery layout", async () => {
    await setupWebsiteBuilder(
        `
        <section class="s_image_gallery o_masonry" data-columns="2">
            <div class="container">
                <div class="o_masonry_col col-lg-6">
                    <img class="first_img img img-fluid d-block rounded" data-index="1" src='${dummyBase64Img}'>
                </div>
                <div class="o_masonry_col col-lg-6">
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="5"  src='${dummyBase64Img}'>
                </div>
            </div>
        </section>
        `
    );
    await contains(":iframe .first_img").click();
    await waitFor("[data-label='Mode']");
    expect("[data-label='Mode']").toHaveCount(1);
    expect(queryOne("[data-label='Mode'] .dropdown-toggle").textContent).toBe("Masonry");
    await contains("[data-label='Mode'] .dropdown-toggle").click();

    await contains("[data-action-param='grid']").click();
    await waitFor(":iframe .o_grid");
    expect(":iframe .o_grid").toHaveCount(1);
    expect(":iframe .o_masonry_col").toHaveCount(0);
    expect(queryOne("[data-label='Mode'] .dropdown-toggle").textContent).toBe("Grid");
});

test("Change gallery restore the container to the cloned equivalent image", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `
        <section class="s_image_gallery o_masonry" data-columns="2">
            <div class="container">
                <div class="o_masonry_col col-lg-6">
                    <img class="first_img img img-fluid d-block rounded" data-index="1" src='${dummyBase64Img}'>
                </div>
                <div class="o_masonry_col col-lg-6">
                    <img class="a_nice_img img img-fluid d-block rounded" data-index="5"  src='${dummyBase64Img}'>
                </div>
            </div>
        </section>
        `
    );
    const editor = getEditor();
    const builderOptions = editor.shared["builder-options"];
    const expectOptionContainerToInclude = (elem) => {
        expect(builderOptions.getContainers().map((container) => container.element)).toInclude(
            elem
        );
    };

    await contains(":iframe .first_img").click();
    await contains("[data-label='Mode'] button").click();

    await contains("[data-action-param='grid']").click();
    await waitFor(":iframe .o_grid");

    // The container include the new image equivalent to the old selected image
    expectOptionContainerToInclude(queryOne(":iframe .first_img"));

    await contains(".o-snippets-top-actions .fa-undo").click();
    expectOptionContainerToInclude(queryOne(":iframe .first_img"));
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expectOptionContainerToInclude(queryOne(":iframe .first_img"));
});
