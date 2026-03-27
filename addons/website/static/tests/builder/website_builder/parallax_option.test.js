import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

test("test parallax zoom", async () => {
    await setupWebsiteAndOpenParallaxOptions();
    await contains("[data-action-value='zoomOut']").click();
    await waitFor("[data-label='Intensity'] input");
    expect(":iframe section").not.toHaveStyle("background-image", { inline: true });
    expect("[data-label='Intensity'] input").toBeVisible();
});
test("add parallax changes editing element", async () => {
    await setupWebsiteAndOpenParallaxOptions({}, { loadIframeBundles: true });
    await contains("[data-action-value='fixed']").click();
    await contains("[data-label='Position'] .dropdown-toggle").click();
    await contains("[data-action-value='repeat-pattern']").click();
    expect(":iframe section").not.toHaveClass("o_bg_img_opt_repeat");
    expect(":iframe section .s_parallax_bg").toHaveClass("o_bg_img_opt_repeat");
    expect(":iframe section .s_parallax_bg").toHaveStyle("background-repeat: repeat");
});
test("add parallax removes classes on the original editing element", async () => {
    await setupWebsiteAndOpenParallaxOptions({ editingElClasses: "o_modified_image_to_save" });
    await contains("[data-action-value='fixed']").click();
    expect(":iframe section").not.toHaveClass("o_modified_image_to_save");
    expect(":iframe section .s_parallax_bg").toHaveClass("o_modified_image_to_save");
});
test("remove parallax changes editing element", async () => {
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    await setupWebsiteBuilder(`
        <section>
            <span class='s_parallax_bg oe_img_bg o_bg_img_center' style="background-image: ${backgroundImageUrl} !important;">aaa</span>
        </section>`);
    await contains(":iframe section").click();
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    await contains("[data-action-value='none']").click();
    await contains("[data-label='Position'] .dropdown-toggle").click();
    await contains("[data-action-value='repeat-pattern']").click();
    expect(":iframe section").toHaveClass("o_bg_img_opt_repeat");
});

test("remove parallax from block containing an inner block with parallax", async () => {
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    await setupWebsiteBuilder(`
        <section id="section_a" style="background-image: ${backgroundImageUrl} !important;">
            <section id="section_b">
                <span class='s_parallax_bg oe_img_bg o_bg_img_center' style="background-image: ${backgroundImageUrl} !important;">aaa</span>
            </section>
        </section>`);
    await contains(":iframe section#section_a").click();
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    await contains("[data-action-value='top']").click();
    expect(":iframe section#section_a").toHaveClass("parallax");
    expect(":iframe section#section_a > .s_parallax_bg").toHaveCount();
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    await contains("[data-action-value='none']").click();
    expect(":iframe section#section_a > .s_parallax_bg").not.toHaveCount();
    expect(":iframe section#section_b > .s_parallax_bg").toHaveCount();
});

test("remove parallax from inner block", async () => {
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    await setupWebsiteBuilder(`
            <section
                class="s_parallax_no_overflow_hidden"
                style="background-image: ${backgroundImageUrl}">
                AAAA
                        <section data-name="SectionB" id="section_b" class="s_parallax_no_overflow_hidden"
                        style="background-image: ${backgroundImageUrl}">
                            BBBB
                        </section>
            </section>`);
    await contains(":iframe section#section_b").click();
    await contains(
        "[data-container-title='SectionB'] [data-label='Scroll Effect'] button.o-dropdown"
    ).click();
    await contains("[data-action-value='top']").click();
    expect(":iframe section#section_b").toHaveClass("parallax");
    expect(":iframe section#section_b > .s_parallax_bg").toHaveCount();

    await contains(
        "[data-container-title='SectionB'] [data-label='Scroll Effect'] button.o-dropdown"
    ).click();
    await contains("[data-action-value='none']").click();
    expect(":iframe section#section_b > .s_parallax_bg").not.toHaveCount();
});

test("parallax scroll effect 'none' doesn't remove the color filter", async () => {
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    await setupWebsiteBuilder(`
        <section>
            <span class='s_parallax_bg oe_img_bg o_bg_img_center' style="background-image: ${backgroundImageUrl} !important;">aaa</span>
            <div class="o_we_bg_filter" style="background-color: rgba(80, 80, 80, 50);" contenteditable="false"></div>
        </section>`);
    await contains(":iframe section").click();
    expect(":iframe section .o_we_bg_filter").toHaveCount(1);
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    await contains("[data-action-value='none']").click();
    expect(":iframe section .o_we_bg_filter").toHaveCount(1);
});

async function setupWebsiteAndOpenParallaxOptions(
    { editingElClasses = "" } = {},
    builderOptions = {}
) {
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    const editingElClass = editingElClasses ? `class=${editingElClasses}` : "";
    const websiteBuilder = await setupWebsiteBuilder(
        `
        <section ${editingElClass} style="background-image: ${backgroundImageUrl}; width: 500px; height:500px">
        </section>`,
        builderOptions
    );
    await contains(":iframe section").click();
    await websiteBuilder.waitSidebarUpdated();
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    return websiteBuilder;
}
