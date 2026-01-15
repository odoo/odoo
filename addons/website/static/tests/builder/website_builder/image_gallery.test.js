import {
    confirmAddSnippet,
    dummyBase64Img,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";
import { expect, test } from "@odoo/hoot";
import { click, queryAll, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains, dataURItoBlob, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { uniqueId } from "@web/core/utils/functions";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

async function setupWbsiteBuilderWithImageWall() {
    const builder = await setupWebsiteBuilderWithSnippet("s_images_wall");
    queryAll(":iframe img").forEach((imgEl) => (imgEl.src = dummyBase64Img));
    builder.getEditor().shared.history.addStep();
    return builder;
}

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

    onRpc("/web/image/hoot.png", () => {
        const base64Image =
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=";
        return dataURItoBlob(base64Image);
    });

    await setupWbsiteBuilderWithImageWall();
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
    await contains(":iframe .o_masonry_col img[data-index='1']").click();
    await waitFor("[data-action-id='addImage']");
    expect("[data-action-id='addImage']").toHaveCount(1);
    await contains("[data-action-id='addImage']").click();
    // We use "click" instead of contains.click because contains wait for the image to be visible.
    // In this test we don't want to wait ~800ms for the image to be visible but we can still click on it
    await click(".o_existing_attachment_cell .o_button_area");
    await contains(".modal-footer button:not([disabled]):contains(Add)").click();
    await waitFor(":iframe .o_masonry_col img[data-index='6']");

    const columns = queryAll(":iframe .o_masonry_col");
    const columnImgs = columns.map((column) =>
        [...column.children].map((img) => img.dataset.index)
    );

    expect(columnImgs).toEqual([["0", "3", "4", "5", "6"], ["1"], ["2"]]);
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
    const { waitSidebarUpdated } = await setupWbsiteBuilderWithImageWall();

    await contains(":iframe img").click();
    await waitSidebarUpdated();
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
    const builder = await setupWbsiteBuilderWithImageWall();

    const editor = builder.getEditor();
    const builderOptions = editor.shared.builderOptions;
    const expectOptionContainerToInclude = (elem) => {
        expect(builderOptions.getContainers().map((container) => container.element)).toInclude(
            elem
        );
    };

    await contains(":iframe img[data-index='1']").click();
    await contains("[data-label='Mode'] button").click();

    await contains("[data-action-param='grid']").click();
    await waitFor(":iframe .o_grid");

    // The container include the new image equivalent to the old selected image
    expectOptionContainerToInclude(queryOne(":iframe img[data-index='1']"));

    await contains(".o-snippets-top-actions .fa-undo").click();
    expectOptionContainerToInclude(queryOne(":iframe img[data-index='1']"));
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expectOptionContainerToInclude(queryOne(":iframe img[data-index='1']"));
});

test("Change gallery layout when images have a link", async () => {
    await setupWbsiteBuilderWithImageWall();

    await contains(":iframe img[data-index='1']").click();
    await waitFor("[data-label='Mode']");
    await contains("[data-label='Media'] button[data-action-id='setLink']").click();

    await contains("[data-label='Your URL'] [data-action-id='setUrl'] > input").fill(
        "http://odoo.com"
    );
    expect(":iframe section a[href='http://odoo.com'] > img[data-index='1']").toHaveCount(1);

    await contains("[data-label='Mode'] .dropdown-toggle").click();
    await contains("[data-action-param='grid']").click();
    await waitFor(":iframe .o_grid");

    expect(":iframe .o_grid").toHaveCount(1);
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

test("Change gallery layout still works when img.decode() fails", async () => {
    // to handle the Chrome bug where img.decode() can fail with "EncodingError:
    // The source image cannot be decoded" when decoding many images simultaneously.
    // See: https://bugs.chromium.org/p/chromium/issues/detail?id=1256288
    // To reproduce the issue in the test we will set image src = "".
    const builder = await setupWebsiteBuilderWithSnippet("s_images_wall");
    // Change img source so decoding will fail
    const images = queryAll(":iframe img");
    images.forEach((imgEl) => {
        imgEl.src = "";
    });
    await images.at(0).click();
    await builder.waitSidebarUpdated();
    await contains("[data-label='Mode'] .dropdown-toggle").click();

    // This should NOT throw an error even img.decode() call will fail
    await contains("[data-action-param='grid']").click();
    await builder.waitSidebarUpdated();

    // Verify the layout change worked despite decode failures
    expect(":iframe .o_grid").toHaveCount(1);
    expect(":iframe .o_masonry_col").toHaveCount(0);
    expect("[data-label='Mode'] .dropdown-toggle").toHaveText("Grid");
});
