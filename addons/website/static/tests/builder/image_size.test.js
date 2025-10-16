import { expect, test } from "@odoo/hoot";
import { animationFrame, clear, fill, press, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { testImg, testImgSrc, testGifImg, testGifImgSrc } from "./image_test_helpers";

defineWebsiteModels();

test("the image should show its size", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    const selector = `[data-container-title="Image"] [title="Size"]`;
    await waitFor(selector);
    const size = parseFloat(document.querySelector(selector).innerHTML);
    expectAround(size, 22.8);
});

test("the background image should show its size", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            <section style="background-image: url(${testImgSrc});">text</section>
        </div>
    `);
    await contains(":iframe .test-options-target section").click();
    await waitSidebarUpdated();
    const selector = `[data-label="Image"] [title="Size"]`;
    await waitFor(selector);
    const size = parseFloat(document.querySelector(selector).innerHTML);
    expectAround(size, 22.8);
});

function expectAround(value, expected, delta = 0.2) {
    expect(value).toBeGreaterThan(expected - delta);
    expect(value).toBeLessThan(expected + delta);
}

test("the GIF image should NOT show its size", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testGifImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    expect(`[data-label="Image"] [title="Size"]`).toHaveCount(0);
});

test("the GIF background image should NOT show its size", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            <section style="background-image: url(${testGifImgSrc});">text</section>
        </div>
    `);
    await contains(":iframe .test-options-target section").click();
    await waitSidebarUpdated();
    expect(`[data-label="Image"] [title="Size"]`).toHaveCount(0);
});

test("images can be resized by slider, text input and button", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    expect(".options-container [data-action-id='mediaSizeSlider'] input").toHaveValue(99);
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");

    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("9");
    await animationFrame();
    //min width is clipped to 10%
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "10% !important" },
        { inline: true }
    );

    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("110");
    await animationFrame();
    //max width is clipped to 100%
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "100% !important" },
        { inline: true }
    );

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("50");
    await animationFrame();
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "50% !important" },
        { inline: true }
    );

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container button[data-action-id='setMediaSizeAuto']").click();
    await animationFrame();
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "auto !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeSlider'] input").click();
    await clear();
    await fill("65");
    await waitSidebarUpdated();
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "65% !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("65%");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").not.toHaveClass(
        "active"
    );

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await press("Enter");
    await waitSidebarUpdated();
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "auto !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");
});

test("videos can be resized by slider, text input and button", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <figure class="figure">
            <div data-oe-expression="//www.youtube.com/embed/G8b4UZIcTfg?rel=0&amp;autoplay=0" class="figure-img media_iframe_video">
                <iframe src="//www.youtube.com/embed/G8b4UZIcTfg?rel=0&amp;autoplay=0"></iframe>
            </div>
        </figure>
    `);
    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    expect(".options-container [data-action-id='mediaSizeSlider'] input").toHaveValue(99);
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");

    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("9");
    await animationFrame();
    //min width is clipped to 10%
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "10% !important" },
        { inline: true }
    );

    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("110");
    await animationFrame();
    //max width is clipped to 100%
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "100% !important" },
        { inline: true }
    );

    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("50");
    await animationFrame();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "50% !important" },
        { inline: true }
    );

    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    await contains(".options-container button[data-action-id='setMediaSizeAuto']").click();
    await animationFrame();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "auto !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");

    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeSlider'] input").click();
    await clear();
    await fill("65");
    await waitSidebarUpdated();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "65% !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("65%");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").not.toHaveClass(
        "active"
    );

    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await press("Enter");
    await waitSidebarUpdated();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "auto !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");
});

test("images can be resized by slider, text input and button (grid mode)", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="container">
            <div class="row o_grid_mode" data-row-count="8" style="gap: 16px;">
                <div class="test-options-target o_grid_item o_grid_item_image g-height-8 g-col-lg-5 col-lg-5 text-center rounded-4 o_colored_level o_draggable" data-name="Block" style="z-index: 1; grid-area: 1 / 5 / 9 / 10;">
                    <img src="/web/image/website.s_masonry_block_default_image_1" class="img img-fluid mx-auto" alt="" loading="lazy" data-mimetype="image/webp">
                </div>
            </div>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    expect(".options-container [data-action-id='mediaSizeSlider'] input").toHaveValue(99);
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");

    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("9");
    await animationFrame();
    //min width is clipped to 10%
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "10% !important" },
        { inline: true }
    );

    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("110");
    await animationFrame();
    //max width is clipped to 100%
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "100% !important" },
        { inline: true }
    );

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("50");
    await animationFrame();
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "50% !important" },
        { inline: true }
    );

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container button[data-action-id='setMediaSizeAuto']").click();
    await animationFrame();
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "auto !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeSlider'] input").click();
    await clear();
    await fill("65");
    await waitSidebarUpdated();
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "65% !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("65%");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").not.toHaveClass(
        "active"
    );

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await press("Enter");
    await waitSidebarUpdated();
    expect(":iframe .test-options-target img").toHaveStyle(
        { width: "auto !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");
});

test("videos can be resized by slider, text input and button (grid mode)", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="container">
            <div class="row o_grid_mode" data-row-count="8" style="gap: 16px;">
                <div class="o_grid_item o_grid_item_image g-height-8 text-center rounded-4 o_colored_level g-col-lg-12 col-lg-12" data-name="Block" style="z-index: 1; grid-area: 1 / 1 / 9 / 13;">
                    <div data-oe-expression="//www.youtube.com/embed/G8b4UZIcTfg?rel=0&amp;autoplay=0" class="mx-auto media_iframe_video">
                        <div class="css_editable_mode_display"></div>
                        <div class="media_iframe_video_size"></div>
                        <iframe loading="lazy" frameborder="0" allowfullscreen="allowfullscreen" src="//www.youtube.com/embed/G8b4UZIcTfg?rel=0&amp;autoplay=0"></iframe>
                    </div>
                </div>
            </div>
        </div>
    `);
    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    expect(".options-container [data-action-id='mediaSizeSlider'] input").toHaveValue(99);
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");

    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("9");
    await animationFrame();
    //min width is clipped to 10%
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "10% !important" },
        { inline: true }
    );

    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("110");
    await animationFrame();
    //max width is clipped to 100%
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "100% !important" },
        { inline: true }
    );

    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await fill("50");
    await animationFrame();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "50% !important" },
        { inline: true }
    );

    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    await contains(".options-container button[data-action-id='setMediaSizeAuto']").click();
    await animationFrame();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "auto !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");

    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeSlider'] input").click();
    await clear();
    await fill("65");
    await waitSidebarUpdated();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "65% !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("65%");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").not.toHaveClass(
        "active"
    );

    await contains(":iframe .media_iframe_video").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-action-id='mediaSizeText'] input").click();
    await clear();
    await press("Enter");
    await waitSidebarUpdated();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "auto !important" },
        { inline: true }
    );
    expect(".options-container [data-action-id='mediaSizeText'] input").toHaveValue("auto");
    expect(".options-container button[data-action-id='setMediaSizeAuto']").toHaveClass("active");
});
