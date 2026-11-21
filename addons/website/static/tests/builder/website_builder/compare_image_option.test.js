import { expect, test } from "@odoo/hoot";
import { queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const compareImageHtml = `
    <figure class="s_compare_image" data-snippet="s_compare_image" data-name="Compare Image" style="--compare-pos: 50%;">
        <div class="s_compare_image_frame">
            <img class="s_compare_image_before o_snippet_not_selectable" data-mimetype="image/png" src="/base/static/img/logo_white.png" alt=""/>
            <img class="s_compare_image_after o_snippet_not_selectable" data-mimetype="image/png" src="/base/static/img/logo_white.png" alt=""/>
            <div class="s_compare_image_labels">
                <span class="s_compare_image_label badge">Before</span>
                <span class="s_compare_image_label badge">After</span>
            </div>
            <div class="s_compare_image_divider o_not_editable"></div>
        </div>
        <figcaption>Caption</figcaption>
    </figure>
`;

test("clicking an image unfolds the snippet options", async () => {
    await setupWebsiteBuilder(compareImageHtml);
    await contains(":iframe .s_compare_image_after").click();
    await waitFor("[data-container-title='Compare Image']");

    expect(
        "[data-container-title='Compare Image'] > .o_hb_options_container_header > .o_hb_options_container_label"
    ).toHaveAttribute("aria-expanded", "true");
});

test("double-clicking an image opens the media dialog to replace it", async () => {
    await setupWebsiteBuilder(compareImageHtml);
    await contains(":iframe .s_compare_image_before").dblclick();

    await waitFor(".o_select_media_dialog");
});

test("the labels alignment follows the orientation", async () => {
    await setupWebsiteBuilder(compareImageHtml);
    await contains(":iframe .s_compare_image").click();
    await waitFor("[data-label='Labels']");
    expect(queryAllTexts("[data-label='Labels'] button")).toEqual(["Top", "Center", "Bottom"]);

    await contains("[data-label='Labels'] button[title='Bottom']").click();
    expect(":iframe .s_compare_image_labels").toHaveClass("align-items-end");

    await contains("[data-label='Orientation'] button:contains('Horizontal')").click();
    expect(":iframe .s_compare_image").toHaveClass("s_compare_image_horizontal");
    expect(queryAllTexts("[data-label='Labels'] button")).toEqual(["Left", "Center", "Right"]);
    expect("[data-label='Labels'] button[title='Right']").toHaveClass("active");
});

test("the size is set on the frame both images span", async () => {
    await setupWebsiteBuilder(compareImageHtml);
    await contains(":iframe .s_compare_image").click();
    await waitFor("[data-action-id='mediaSizeText']");
    expect("[data-action-id='mediaSizeText']").toHaveCount(1);

    await contains("[data-action-id='mediaSizeText'] input").edit("50");
    expect(":iframe .s_compare_image_frame").toHaveAttribute("style", "width: 50% !important;");
    expect(":iframe .s_compare_image_before").not.toHaveAttribute("style");
});
