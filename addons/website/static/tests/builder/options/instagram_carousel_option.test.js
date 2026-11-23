import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";
import { confirmAddSnippet, waitForEndOfOperation } from "@html_builder/../tests/helpers";
import {
    defineWebsiteModels,
    insertCategorySnippet,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

class WebsiteInstagramAccount extends models.Model {
    _name = "website.instagram.account";
    _records = [{ id: 1, name: "odoo" }];
    name = fields.Char();

    // Instagram only accepts the access token of the "acme" account.
    connect(accessToken) {
        return accessToken === "acme_token" && this.create({ name: "acme" });
    }
}

defineWebsiteModels();
defineModels([WebsiteInstagramAccount]);

const snippetSelector = ":iframe .s_dynamic_snippet_instagram";

async function connectAccount(accessToken) {
    await contains(".modal #instagram_access_token").edit(accessToken);
    await contains(".modal-footer button:contains(Connect)").click();
}

async function selectOption(label, itemSelector) {
    await contains(`[data-label='${label}'] .dropdown-toggle`).click();
    await contains(`.o_popover ${itemSelector}`).click();
}

test("Drop Instagram Carousel snippet and verify snippet options", async () => {
    await setupWebsiteBuilder("");
    await insertCategorySnippet({ group: "social", snippet: "s_dynamic_snippet_instagram" });
    // Default values: the first connected account is displayed.
    expect(snippetSelector).toHaveAttribute("data-instagram-account-id", "1");
    expect(snippetSelector).toHaveAttribute("data-number-of-records", "8");
    expect(snippetSelector).toHaveAttribute("data-number-of-elements", "4");
    expect(snippetSelector).toHaveAttribute("data-carousel-interval", "5000");
    await contains(snippetSelector).click();

    // Section Title
    await contains(
        "[data-label='Section Title'] [data-action-param*='s_dynamic_snippet_title_aside']"
    ).click();
    expect(`${snippetSelector} .s_dynamic_snippet_title`).toHaveClass(
        "s_dynamic_snippet_title_aside"
    );

    // Arrows
    await selectOption("Arrows", "[data-class-action='o_hidden_arrows']");
    expect(snippetSelector).toHaveClass("o_hidden_arrows");

    // Position
    await selectOption("Position", "[data-class-action='o_arrows_inside']");
    expect(snippetSelector).toHaveClass("o_arrows_inside");

    // Color
    await selectOption("Color", "[data-class-action='o_light_arrows']");
    expect(snippetSelector).toHaveClass("o_light_arrows");

    // Slider Speed
    await contains("[data-label='Slider Speed'] input").edit("3");
    expect(snippetSelector).toHaveAttribute("data-carousel-interval", "3000");

    // Scrolling Mode
    await contains("[data-class-action='o_carousel_multi_items']").click();
    expect(snippetSelector).toHaveClass("o_carousel_multi_items");

    // Account
    await contains("button[title='Connect an Instagram account']").click();
    await connectAccount("acme_token");
    await waitFor(`${snippetSelector}[data-instagram-account-id='2']`);
    await selectOption("Account", ".o-dropdown-item:contains(odoo)");
    expect(snippetSelector).toHaveAttribute("data-instagram-account-id", "1");

    // Image Format
    await contains("[data-class-action='o_instagram_portrait']").click();
    expect(snippetSelector).toHaveClass("o_instagram_portrait");

    // Profile, Caption, Likes & Comments
    for (const className of [
        "o_instagram_show_profile",
        "o_instagram_show_caption",
        "o_instagram_show_metrics",
    ]) {
        await contains(`[data-class-action='${className}'] input`).click();
        expect(snippetSelector).not.toHaveClass(className);
    }

    // Post Style: tiles only display the pictures.
    await contains("[data-class-action='o_instagram_tile']").click();
    expect(snippetSelector).toHaveClass("o_instagram_tile");
    expect("[data-label='Profile']").toHaveCount(0);

    // Number of Posts: a single post does not slide.
    await selectOption("Number of Posts", "[data-data-attribute-action-value='6']");
    expect(snippetSelector).toHaveAttribute("data-number-of-records", "6");
    await selectOption("Number of Posts", "[data-data-attribute-action-value='1']");
    expect("[data-label='Slider Speed']").toHaveCount(0);
    expect("[data-label='Scrolling Mode']").toHaveCount(0);

    // Posts per Slide
    await selectOption("Posts per Slide", "[data-data-attribute-action-value='2']");
    expect(snippetSelector).toHaveAttribute("data-number-of-elements", "2");
});

test("Drop Instagram Carousel snippet without connected account", async () => {
    onRpc("website.instagram.account", "name_search", () => []);
    await setupWebsiteBuilder("");
    await contains(
        "#snippet_groups .o_snippet[data-snippet-group=social] .o_snippet_thumbnail_area"
    ).click();
    await confirmAddSnippet("s_dynamic_snippet_instagram");
    // The drop waits for an account to be connected.
    await connectAccount("wrong_token");
    expect(".modal .text-danger").toHaveText("Instagram did not accept this access token.");
    await connectAccount("acme_token");
    await waitForEndOfOperation();
    expect(snippetSelector).toHaveAttribute("data-instagram-account-id", "2");
});
