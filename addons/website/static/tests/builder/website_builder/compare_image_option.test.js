import { expect, test } from "@odoo/hoot";
import { queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { getCompareImageXml } from "@website/../tests/interactions/snippets/helpers";

defineWebsiteModels();

test("clicking an image opens the snippet options, double-clicking it replaces it by an image", async () => {
    await setupWebsiteBuilder(getCompareImageXml());
    await contains(":iframe .s_compare_image_after").click();
    await waitFor("[data-container-title='Compare Image']");

    expect(
        "[data-container-title='Compare Image'] > .o_hb_options_container_header > .o_hb_options_container_label"
    ).toHaveAttribute("aria-expanded", "true");

    await contains(":iframe .s_compare_image_before").dblclick();
    await waitFor(".o_select_media_dialog");
    expect(queryAllTexts(".o_select_media_dialog .nav-tabs .nav-item")).toEqual(["Images"]);
});

test("each image section follows the state of its own image", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(getCompareImageXml());
    await contains(":iframe .s_compare_image").click();
    await contains("[data-container-title='Before'] [data-action-id='setLink']").click();
    await waitSidebarUpdated();
    expect("[data-container-title='Before'] [data-label='Your URL']").toHaveCount(1);
    expect("[data-container-title='After'] [data-label='Your URL']").toHaveCount(0);
});

test("the labels alignment follows the orientation, and hiding the labels hides it", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(getCompareImageXml());
    await contains(":iframe .s_compare_image").click();
    await waitFor("[data-label='Alignment']");
    expect("[data-label='Labels'] input").toBeChecked();
    expect(queryAllTexts("[data-label='Alignment'] button")).toEqual(["Top", "Center", "Bottom"]);

    await contains("[data-label='Alignment'] button:contains('Bottom')").click();
    expect(":iframe .s_compare_image_labels").toHaveClass("align-items-end");

    await contains("[data-label='Orientation'] button:contains('Horizontal')").click();
    expect(":iframe .s_compare_image").toHaveClass("s_compare_image_horizontal");
    expect(queryAllTexts("[data-label='Alignment'] button")).toEqual(["Left", "Center", "Right"]);
    expect("[data-label='Alignment'] button:contains('Right')").toHaveClass("active");

    await contains("[data-label='Labels'] .o-checkbox").click();
    await waitSidebarUpdated();
    expect(":iframe .s_compare_image_labels").toHaveClass("d-none");
    expect("[data-label='Alignment']").toHaveCount(0);
});

test("the initial position of divider is set on the snippet, the size on the frame only", async () => {
    await setupWebsiteBuilder(getCompareImageXml());
    await contains(":iframe .s_compare_image").click();
    await waitFor("[data-action-id='mediaSizeText']");
    expect("[data-action-id='mediaSizeText']").toHaveCount(1);

    await contains("[data-label='Initial position'] .o_hb_input_number").edit("70");
    expect(":iframe .s_compare_image").toHaveAttribute("style", "--s_compare_image-position: 70%;");

    await contains("[data-action-id='mediaSizeText'] input").edit("50");
    expect(":iframe .s_compare_image_frame").toHaveAttribute("style", "width: 50% !important;");
});
