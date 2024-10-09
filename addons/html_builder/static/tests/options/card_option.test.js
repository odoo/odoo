import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { click, queryOne, setInputRange, waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

const cardHtml = `
    <div class="s_card" data-snippet="s_card" data-name="Card">
        <div class="card-body">
            <h5 class="card-title">Card title</h5>
            <p class="card-text">Card text</p>
        </div>
    </div>`;

test("set card width", async () => {
    await setupWebsiteBuilder(cardHtml);
    await contains(":iframe .s_card").click();
    expect("[data-action-id='setCardWidth']").toHaveCount(1);
    expect(queryOne(":iframe .s_card").style.maxWidth).toBeEmpty();
    // Default value for range input is 100%
    expect("[data-action-id='setCardWidth'] input").toHaveValue(100);

    await setInputRange("[data-action-id='setCardWidth'] input", 50);
    expect(":iframe .s_card").toHaveStyle({ maxWidth: "50%" });
});

test("set card aligment", async () => {
    await setupWebsiteBuilder(cardHtml);
    await contains(":iframe .s_card").click();
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
    expect(":iframe .s_card").toHaveClass("mx-auto");

    await click("[data-label='Alignment'] button[title='Right']");
    expect(":iframe .s_card").toHaveClass("ms-auto");

    await click("[data-label='Alignment'] button[title='Left']");
    expect(":iframe .s_card").toHaveClass("me-auto");
});
