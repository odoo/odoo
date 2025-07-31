import { expect, test } from "@odoo/hoot";
import { click, queryAll, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains, dataURItoBlob, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    dummyBase64Img,
    setupWebsiteBuilder,
    confirmAddSnippet,
    waitForEndOfOperation,
} from "../website_helpers";
import { uniqueId } from "@web/core/utils/functions";

defineWebsiteModels();

test("Add image in gallery", async () => {
    onRpc("ir.attachment", "search_read", () => [
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

    const { waitDomUpdated } = await setupWebsiteBuilder(
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
    await waitDomUpdated();
    await contains(".modal-footer button").click();
    await waitFor(":iframe .o_masonry_col img[data-index='6']");

    const columns = queryAll(":iframe .o_masonry_col");
    const columnImgs = columns.map((column) =>
        [...column.children].map((img) => img.dataset.index)
    );

    expect(columnImgs).toEqual([["1", "3", "4", "5", "6"], ["2"]]);
    expect.verifySteps(["get_image_info", "get_image_info"]);
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
    const builderOptions = editor.shared["builderOptions"];
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

test("Dropping multiple image galleries should produce unique IDs", async () => {
    await setupWebsiteBuilder("");
    patchWithCleanup(uniqueId, { nextId: 0 });

    const imageSnippetButtonSelector =
        ".o-website-builder_sidebar  #snippet_groups .o_snippet[name='Images'] button";
    for (let i = 0; i < 2; i++) {
        await contains(imageSnippetButtonSelector).click();
        await confirmAddSnippet("s_image_gallery");
        await waitForEndOfOperation();
    }
    expect(":iframe .s_image_gallery:nth-child(1) .carousel").toHaveAttribute("id");
    expect(":iframe .s_image_gallery:nth-child(2) .carousel").toHaveAttribute("id");
    const imageCarousels = queryAll(":iframe .s_image_gallery .carousel");
    expect(imageCarousels[0].id).not.toEqual(imageCarousels[1].id);
});

test("Cloning an image gallery should produce a unique ID", async () => {
    await setupWebsiteBuilder("");
    patchWithCleanup(uniqueId, { nextId: 0 });

    const imageSnippetButtonSelector =
        ".o-website-builder_sidebar  #snippet_groups .o_snippet[name='Images'] button";
    await contains(imageSnippetButtonSelector).click();
    await confirmAddSnippet("s_image_gallery");
    await waitForEndOfOperation();
    expect(":iframe .s_image_gallery").toHaveCount(1);

    await contains(":iframe .s_image_gallery").click();
    await contains(".o_snippet_clone").click();
    expect(":iframe .s_image_gallery:nth-child(1) .carousel").toHaveAttribute("id");
    expect(":iframe .s_image_gallery:nth-child(2) .carousel").toHaveAttribute("id");
    const imageCarousels = queryAll(":iframe .s_image_gallery .carousel");
    expect(imageCarousels[0].id).not.toEqual(imageCarousels[1].id);
});
