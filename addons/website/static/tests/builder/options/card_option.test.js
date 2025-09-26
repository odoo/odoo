import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { dummyBase64Img } from "@html_builder/../tests/helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { animationFrame, click, queryOne, setInputRange, waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

const simpleCardHtml = `
    <div class="s_card" data-snippet="s_card" data-name="Card">
        <div class="card-body">
            <h5 class="card-title">Card title</h5>
            <p class="card-text">Card text</p>
        </div>
    </div>`;

test("set card width", async () => {
    await setupWebsiteBuilder(simpleCardHtml);
    await contains(":iframe .s_card").click();
    await waitFor("[data-action-id='setCardWidth']");
    expect("[data-action-id='setCardWidth']").toHaveCount(1);
    expect(queryOne(":iframe .s_card").style.maxWidth).toBeEmpty();
    // Default value for range input is 100%
    expect("[data-action-id='setCardWidth'] input").toHaveValue(100);

    await setInputRange("[data-action-id='setCardWidth'] input", 50);
    await animationFrame();
    expect(":iframe .s_card").toHaveStyle({ maxWidth: "50%" });
});

test("set card alignment", async () => {
    await setupWebsiteBuilder(simpleCardHtml);
    await contains(":iframe .s_card").click();
    await waitFor("[data-action-id='setCardWidth'] input");
    expect("[data-action-id='setCardWidth'] input").toHaveValue(100);
    // Alignment option not available when card width is 100%
    expect("[data-label='Alignment']").toHaveCount(0);

    await setInputRange("[data-action-id='setCardWidth'] input", 50);
    await waitFor("[data-label='Alignment']");
    expect("[data-label='Alignment']").toHaveCount(1);

    expect(":iframe .s_card").not.toHaveClass(["me-auto", "mx-auto", "ms-auto"]);
    // Left alignment button is active by default
    expect("[data-label='Alignment'] button[title='Left']").toHaveClass("active");

    await click("[data-label='Alignment'] button[title='Center']");
    await animationFrame();
    expect(":iframe .s_card").toHaveClass("mx-auto");

    await click("[data-label='Alignment'] button[title='Right']");
    await animationFrame();
    expect(":iframe .s_card").toHaveClass("ms-auto");

    await click("[data-label='Alignment'] button[title='Left']");
    await animationFrame();
    expect(":iframe .s_card").toHaveClass("me-auto");
});

const cardWithImageHtml = `
    <div class="s_card o_card_img_top card o_cc o_cc1" data-vxml="001" data-snippet="s_card" data-name="Card">
        <figure class="o_card_img_wrapper ratio ratio-16x9 mb-0">
            <img class="o_card_img card-img-top" src="${dummyBase64Img}" alt="" loading="lazy">
        </figure>
        <div class="card-body">
            <h5 class="card-title">Card title</h5>
            <p class="card-text">Card content</p>
        </div>
    </div>`;

test("remove/add cover image", async () => {
    await setupWebsiteBuilder(cardWithImageHtml);
    await contains(":iframe .s_card").click();
    await waitFor("[data-action-id='removeCoverImage']");
    // Button to remove cover image is available
    expect("[data-action-id='removeCoverImage']").toHaveCount(1);
    // Button to add cover image is not available
    expect("[data-action-id='addCoverImage']").toHaveCount(0);
    // Remove cover image
    await click("[data-action-id='removeCoverImage']");
    expect(":iframe .s_card .o_card_img_wrapper").toHaveCount(0);
    expect(":iframe .s_card").not.toHaveClass("o_card_img_top");
    await waitFor("[data-action-id='addCoverImage']");
    // Button to remove cover image is no longer available
    expect("[data-action-id='removeCoverImage']").toHaveCount(0);
    // Button to add cover image is now available
    expect("[data-action-id='addCoverImage']").toHaveCount(1);
    // Add cover image back again
    await click("[data-action-id='addCoverImage']");
    expect(":iframe .s_card .o_card_img_wrapper").toHaveCount(1);
});

test("set cover image position", async () => {
    await setupWebsiteBuilder(cardWithImageHtml);
    await contains(":iframe .s_card").click();
    await waitFor("[data-action-id='setCoverImagePosition']");
    // As per html content: image is on top
    expect(":iframe .s_card").toHaveClass("o_card_img_top");
    expect(":iframe .s_card .o_card_img").toHaveClass("card-img-top");
    // Top position is active
    expect("[data-action-id='setCoverImagePosition'][title='Top']").toHaveClass("active");

    // Set image position to left
    await click("[data-action-id='setCoverImagePosition'][title='Left']");
    await waitFor("[data-action-id='setCoverImagePosition'][title='Left'].active");
    expect(":iframe .s_card").toHaveClass(["o_card_img_horizontal", "flex-lg-row"]);
    expect(":iframe .s_card .o_card_img").toHaveClass("rounded-start");

    // Set image position to right
    await click("[data-action-id='setCoverImagePosition'][title='Right']");
    await waitFor("[data-action-id='setCoverImagePosition'][title='Right'].active");
    expect(":iframe .s_card").toHaveClass(["o_card_img_horizontal", "flex-lg-row-reverse"]);
    expect(":iframe .s_card .o_card_img").toHaveClass("rounded-end");

    // Set image position back to top
    await click("[data-action-id='setCoverImagePosition'][title='Top']");
    await waitFor("[data-action-id='setCoverImagePosition'][title='Top'].active");
    expect(":iframe .s_card").toHaveClass("o_card_img_top");
    expect(":iframe .s_card .o_card_img").toHaveClass("card-img-top");

    // Remove cover image
    await click("[data-action-id='removeCoverImage']");
    await waitFor("[data-action-id='addCoverImage']");
    // Position buttons are no longer available
    expect("[data-action-id='setCoverImagePosition']").toHaveCount(0);
});

async function openRatioDropdownMenu() {
    click("[data-label='Ratio'] .dropdown");
    await waitFor(".popover.dropdown-menu");
}

test("set cover image ratio", async () => {
    await setupWebsiteBuilder(cardWithImageHtml);
    await contains(":iframe .s_card").click();

    // As per html content: image has a 16x9 ratio
    expect(":iframe .s_card .o_card_img_wrapper").toHaveClass(["ratio", "ratio-16x9"]);
    await waitFor("[data-label='Ratio'] ");
    expect("[data-label='Ratio'] .dropdown").toHaveText("Wide - 16/9");

    // Set image ratio to image default
    await openRatioDropdownMenu();
    await click(".dropdown-menu [data-class-action=''");
    await animationFrame();
    expect(":iframe .s_card .o_card_img_wrapper").not.toHaveClass("ratio");

    // Test square, landscape, wide and ultrawide ratios
    for (const ratioClass of ["ratio-1x1", "ratio-4x3", "ratio-16x9", "ratio-21x9"]) {
        await openRatioDropdownMenu();
        await click(`.dropdown-menu [data-class-action='ratio ${ratioClass}']`);
        await animationFrame();
        expect(":iframe .s_card .o_card_img_wrapper").toHaveClass(["ratio", ratioClass]);
    }

    // Set custom ratio
    await openRatioDropdownMenu();
    await click(".dropdown-menu [data-class-action='ratio o_card_img_ratio_custom']");
    await waitFor("[data-label='Custom Ratio'] input[type='range']");
    await setInputRange("[data-label='Custom Ratio'] input[type='range']", 60);
    await animationFrame();
    expect(":iframe .s_card .o_card_img_wrapper").toHaveClass("o_card_img_ratio_custom");
    expect(":iframe .s_card").toHaveStyle({ "--card-img-aspect-ratio": "60%" });
});

test("ratios only supported for top image", async () => {
    await setupWebsiteBuilder(cardWithImageHtml);
    await contains(":iframe .s_card").click();
    await waitFor("[data-label='Ratio'] ");
    await openRatioDropdownMenu();
    // When cover image is on top, all ratios are available
    expect(":iframe .s_card").toHaveClass("o_card_img_top");
    expect(`.dropdown-menu [data-class-action='']`).toHaveCount(1); // Default image ratio
    for (const ratioClass of [
        "ratio-1x1",
        "ratio-4x3",
        "ratio-16x9",
        "ratio-21x9",
        "o_card_img_ratio_custom",
    ]) {
        expect(`.dropdown-menu [data-class-action='ratio ${ratioClass}']`).toHaveCount(1);
    }
    // Set image position to left
    await click("[data-action-id='setCoverImagePosition'][title='Left']");
    await waitFor("[data-action-id='setCoverImagePosition'][title='Left'].active");
    expect(":iframe .s_card").toHaveClass(["o_card_img_horizontal", "flex-lg-row"]);
    await openRatioDropdownMenu();
    // When cover image is left or right, only default and square ratios are available
    expect(`.dropdown-menu [data-class-action='']`).toHaveCount(1); // Default image ratio
    expect(`.dropdown-menu [data-class-action='ratio ratio-1x1']`).toHaveCount(1); // Square
    for (const ratioClass of ["ratio-4x3", "ratio-16x9", "ratio-21x9", "o_card_img_ratio_custom"]) {
        expect(`.dropdown-menu [data-class-action='ratio ${ratioClass}']`).toHaveCount(0);
    }
});

test("set cover image width", async () => {
    await setupWebsiteBuilder(cardWithImageHtml);
    await contains(":iframe .s_card").click();

    // Width option not available when image is on top
    expect("[data-label='Width']").toHaveCount(0);
    // Set image position to left
    await waitFor("[data-action-id='setCoverImagePosition']");
    await click("[data-action-id='setCoverImagePosition'][title='Left']");
    await waitFor("[data-label='Width']");
    // Width option is now available
    expect("[data-label='Width']").toHaveCount(1);
    await setInputRange("[data-label='Width'] input", 25);
    await animationFrame();
    const cardImageWidthValue =
        queryOne(":iframe .s_card").style.getPropertyValue("--card-img-size-h");
    expect(parseFloat(cardImageWidthValue)).toBeWithin(24.9, 25.1);
});

test("cover image set to wide aspect ratio can be vertically aligned", async () => {
    await setupWebsiteBuilder(cardWithImageHtml);
    await contains(":iframe .s_card").click();
    await waitFor("[data-action-id='alignCoverImage']");
    expect("[data-label='Alignment'] [data-action-id='alignCoverImage'").toHaveCount(1);
    await setInputRange("[data-action-id='alignCoverImage'] input", 50);
    await animationFrame();
    expect(":iframe .s_card .o_card_img_wrapper").toHaveClass("o_card_img_adjust_v");
    expect(":iframe .s_card").toHaveStyle({ "--card-img-ratio-align": "50%" });
});
