import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { manuallyDispatchProgrammaticEvent, queryOne, waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

test("test parallax zoom", async () => {
    await setupWebsiteAndOpenParallaxOptions();
    await contains("[data-action-value='zoomOut']").click();
    await waitFor("[data-label='Intensity'] input");
    expect(":iframe section").not.toHaveStyle("background-image", { inline: true });
    expect("[data-label='Intensity'] input").toBeVisible();
});

test("add parallax keeps repeat pattern on background", async () => {
    await setupWebsiteAndOpenParallaxOptions({}, { loadIframeBundles: true });
    await contains("[data-label='Position'] .dropdown-toggle").click();
    await contains("[data-action-value='repeat-pattern']").click();
    expect(":iframe section").toHaveClass("o_bg_img_opt_repeat");
    await contains("[data-label='Scroll Effect'] .dropdown-toggle").click();
    await contains("[data-action-value='fixed']").click();
    // Verify that the repeat pattern is still applied
    expect(":iframe section").not.toHaveClass("o_bg_img_opt_repeat");
    expect(":iframe section .s_parallax_bg").toHaveClass("o_bg_img_opt_repeat");
    expect(":iframe section .s_parallax_bg").toHaveStyle("background-repeat: repeat");
    // Check that the option is still selected in the dropdown
    await contains("[data-label='Position'] .dropdown-toggle").click();
    expect("[data-action-value='repeat-pattern']").toHaveClass("active");
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
            <span class="s_parallax_bg_wrap">
                <span class="s_parallax_bg oe_img_bg o_bg_img_center" style="background-image: ${backgroundImageUrl} !important;">aaa</span>
            </span>
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
                <span class="s_parallax_bg_wrap">
                    <span class="s_parallax_bg oe_img_bg o_bg_img_center" style="background-image: ${backgroundImageUrl} !important;">aaa</span>
                </span>
            </section>
        </section>`);
    await contains(":iframe section#section_a").click();
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    await contains("[data-action-value='top']").click();
    expect(":iframe section#section_a").toHaveClass("parallax");
    expect(":iframe section#section_a > .s_parallax_bg_wrap > .s_parallax_bg").toHaveCount();
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    await contains("[data-action-value='none']").click();
    expect(":iframe section#section_a > .s_parallax_bg_wrap > .s_parallax_bg").not.toHaveCount();
    expect(":iframe section#section_b > .s_parallax_bg_wrap > .s_parallax_bg").toHaveCount();
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
    expect(":iframe section#section_b > .s_parallax_bg_wrap > .s_parallax_bg").toHaveCount();

    await contains(
        "[data-container-title='SectionB'] [data-label='Scroll Effect'] button.o-dropdown"
    ).click();
    await contains("[data-action-value='none']").click();
    expect(":iframe section#section_b > .s_parallax_bg_wrap > .s_parallax_bg").not.toHaveCount();
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

describe("scroll effect", () => {
    beforeEach(async () => {
        await setupWebsiteBuilder(
            `<section style="background-image: url('/web/image/123/transparent.png'); height: 500px">
                <div class="container"><p>Content</p></div>
            </section>`,
            { interactions: ["website.parallax"] }
        );
        await contains(":iframe section").click();
    });

    test("filtered image follows the scroll effect target", async () => {
        await setScrollEffect("fixed");
        await contains("[data-label='Filter'] .dropdown-toggle").click();
        await contains("[data-action-id='glFilter'][data-action-param='blur']").click();
        await waitFor(":iframe .s_parallax_bg[data-gl-filter='blur']");
        expect(":iframe .s_parallax_bg").toHaveClass("o_modified_image_to_save");

        // Without parallax, the section holds the image
        await setScrollEffect("none");
        expect(":iframe .s_parallax_bg").toHaveCount(0);
        expect(":iframe section").toHaveAttribute("data-gl-filter", "blur");
        expect(":iframe section").toHaveClass("o_modified_image_to_save");

        await setScrollEffect("fixed");
        expect(":iframe section").not.toHaveAttribute("data-gl-filter");
        expect(":iframe section").not.toHaveClass("o_modified_image_to_save");
        expect(":iframe .s_parallax_bg").toHaveAttribute("data-gl-filter", "blur");
        expect(":iframe .s_parallax_bg").toHaveClass("o_modified_image_to_save");
    });

    test("interaction moves the background in edit mode", async () => {
        await setScrollEffect("top");
        // Styles set by the interaction, not by the option
        expect(":iframe .s_parallax_bg").toHaveStyle("top; bottom; transform", { inline: true });

        await setScrollEffect("zoomIn");
        expect(":iframe .s_parallax_bg").toHaveStyle({ transform: /^scale\(/ }, { inline: true });
    });
});

test("parallax interaction does not mark the page as dirty", async () => {
    // Changing the option marks the page as dirty, and the test reload
    // restores the initial content: start from a saved "Parallax to Top".
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    await setupWebsiteBuilder(
        `<section class="parallax" data-scroll-background-ratio="1.5" style="height: 500px">
            <span class="s_parallax_bg_wrap">
                <span class="s_parallax_bg oe_img_bg" style="background-image: ${backgroundImageUrl}"></span>
            </span>
        </section>`,
        { interactions: ["website.parallax"] }
    );
    // The interaction first applies its style before the editor observes the
    // DOM: make it update the style in edit mode by moving the section from
    // outside the editable, then scrolling.
    const { transform } = (await waitFor(":iframe .s_parallax_bg[style*='translateY(']")).style;
    const iframeBody = queryOne(":iframe body");
    iframeBody.style.paddingTop = "200px";
    await manuallyDispatchProgrammaticEvent(iframeBody.ownerDocument, "scroll");
    expect(":iframe .s_parallax_bg").not.toHaveStyle({ transform }, { inline: true });
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
});

async function setScrollEffect(value) {
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    await contains(`[data-action-value='${value}']`).click();
}

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
