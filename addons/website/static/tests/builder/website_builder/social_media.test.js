import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { getDragHelper, waitForEndOfOperation } from "@html_builder/../tests/helpers";
import { click, queryOne } from "@odoo/hoot-dom";

defineWebsiteModels();

test("add social medias", async () => {
    onRpc("website", "read", ({ args }) => {
        expect(args[0]).toEqual([1]);
        expect(args[1]).toInclude("social_facebook");
        expect(args[1]).toInclude("social_twitter");
        return [{ id: 1, social_facebook: "https://fb.com/odoo", social_twitter: false }];
    });

    await setupWebsiteBuilder(`<div class="s_social_media"><h4>Social Media</h4></div>`);

    await click(":iframe h4");

    const facebookLinkSelector = ":iframe a[href='/website/social/facebook']";
    expect(facebookLinkSelector).toHaveCount(0);
    const toggleFacebookSelector =
        "td:has([data-action-param='facebook']) + td [data-action-id='toggleRecordedSocialMediaLink'] input[type=checkbox]";
    await contains(toggleFacebookSelector).click();
    expect(facebookLinkSelector).toHaveCount(1);
    await contains(toggleFacebookSelector).click();
    expect(facebookLinkSelector).toHaveCount(0);

    const exampleLinkSelector = ":iframe a[href='https://www.example.com']";
    expect(exampleLinkSelector).toHaveCount(0);
    await contains("button[data-action-id='addSocialMediaLink']").click();
    expect(exampleLinkSelector).toHaveCount(1);
    await contains("button[data-action-id='deleteSocialMediaLink']").click();
    expect(exampleLinkSelector).toHaveCount(0);

    expect("td:has([data-action-param='twitter'])").toHaveCount(1);
});

test("reorder social medias", async () => {
    onRpc("website", "read", ({ args }) => [
        { id: 1, social_facebook: "https://fb.com/odoo", social_twitter: "https://x.com/odoo" },
    ]);

    await setupWebsiteBuilder(`<div class="s_social_media"><h4>Social Media</h4></div>`);

    await click(":iframe h4");

    await contains("td:has([data-action-param='facebook']) + td input[type=checkbox]").click();
    await contains("button[data-action-id='addSocialMediaLink']").click();
    await contains("div[data-action-id='editSocialMediaLink'] input").fill("/first");
    await contains("button[data-action-id='addSocialMediaLink']").click();

    // we don't know the order for the ones received from the server
    expect("tr [data-action-param='facebook'] input").toHaveValue("https://fb.com/odoo");
    expect("tr [data-action-param='twitter'] input").toHaveValue("https://x.com/odoo");
    expect("tr:nth-child(3) input[type=text]").toHaveValue("https://www.example.com/first");
    expect("tr:nth-child(4) input[type=text]").toHaveValue("https://www.example.com");

    expect(":iframe a").toHaveCount(3);
    expect(":iframe a:nth-of-type(1)").toHaveAttribute("href", "/website/social/facebook");
    expect(":iframe a:nth-of-type(2)").toHaveAttribute("href", "https://www.example.com/first");
    expect(":iframe a:nth-of-type(3)").toHaveAttribute("href", "https://www.example.com");

    await contains("td:has(+td [data-action-param='facebook']) button.o_drag_handle").dragAndDrop(
        "tr:last-child"
    );

    expect("tr:nth-child(1) input[type=text]").toHaveValue("https://x.com/odoo");
    expect("tr:nth-child(1) input[type=checkbox]").not.toBeChecked();
    expect("tr:nth-child(2) input[type=text]").toHaveValue("https://www.example.com/first");
    expect("tr:nth-child(3) input[type=text]").toHaveValue("https://www.example.com");
    expect("tr:nth-child(4) input[type=text]").toHaveValue("https://fb.com/odoo");
    expect("tr:nth-child(4) input[type=checkbox]").toBeChecked();

    expect(":iframe a:nth-of-type(1)").toHaveAttribute("href", "https://www.example.com/first");
    expect(":iframe a:nth-of-type(2)").toHaveAttribute("href", "https://www.example.com");
    expect(":iframe a:nth-of-type(3)").toHaveAttribute("href", "/website/social/facebook");

    await contains("tr:nth-child(1) button.o_drag_handle").dragAndDrop("tr:nth-child(2)");

    expect("tr:nth-child(1) input[type=text]").toHaveValue("https://www.example.com/first");
    expect("tr:nth-child(2) input[type=text]").toHaveValue("https://x.com/odoo");
    expect("tr:nth-child(2) input[type=checkbox]").not.toBeChecked();
    expect("tr:nth-child(3) input[type=text]").toHaveValue("https://www.example.com");
    expect("tr:nth-child(4) input[type=text]").toHaveValue("https://fb.com/odoo");
    expect("tr:nth-child(4) input[type=checkbox]").toBeChecked();

    expect(":iframe a:nth-of-type(1)").toHaveAttribute("href", "https://www.example.com/first");
    expect(":iframe a:nth-of-type(2)").toHaveAttribute("href", "https://www.example.com");
    expect(":iframe a:nth-of-type(3)").toHaveAttribute("href", "/website/social/facebook");

    expect(":iframe h4").toHaveCount(1);

    await contains("tr:nth-child(2) input[type=checkbox]").click();
    await contains("tr:nth-child(4) input[type=checkbox]").click();

    expect("tr:nth-child(1) input[type=text]").toHaveValue("https://www.example.com/first");
    expect("tr:nth-child(2) input[type=text]").toHaveValue("https://x.com/odoo");
    expect("tr:nth-child(2) input[type=checkbox]").toBeChecked();
    expect("tr:nth-child(3) input[type=text]").toHaveValue("https://www.example.com");
    expect("tr:nth-child(4) input[type=text]").toHaveValue("https://fb.com/odoo");
    expect("tr:nth-child(4) input[type=checkbox]").not.toBeChecked();

    expect(":iframe a:nth-of-type(1)").toHaveAttribute("href", "https://www.example.com/first");
    expect(":iframe a:nth-of-type(2)").toHaveAttribute("href", "/website/social/twitter");
    expect(":iframe a:nth-of-type(3)").toHaveAttribute("href", "https://www.example.com");

    await contains("tr:nth-child(2) input[type=checkbox]").click();
    await contains("tr:nth-child(4) button.o_drag_handle").dragAndDrop("tr:nth-child(1)");

    expect("tr:nth-child(1) input[type=text]").toHaveValue("https://fb.com/odoo");
    expect("tr:nth-child(1) input[type=checkbox]").not.toBeChecked();
    expect("tr:nth-child(2) input[type=text]").toHaveValue("https://www.example.com/first");
    expect("tr:nth-child(3) input[type=text]").toHaveValue("https://x.com/odoo");
    expect("tr:nth-child(3) input[type=checkbox]").not.toBeChecked();
    expect("tr:nth-child(4) input[type=text]").toHaveValue("https://www.example.com");

    expect(":iframe a:nth-of-type(1)").toHaveAttribute("href", "https://www.example.com/first");
    expect(":iframe a:nth-of-type(2)").toHaveAttribute("href", "https://www.example.com");

    await contains("tr:nth-child(3) input[type=checkbox]").click();
    await contains("tr:nth-child(3) button.o_drag_handle").dragAndDrop("tr:nth-child(1)");
    await contains("tr:nth-child(3) button.o_drag_handle").dragAndDrop("tr:nth-child(1)");

    expect("tr:nth-child(1) input[type=text]").toHaveValue("https://www.example.com/first");
    expect("tr:nth-child(2) input[type=text]").toHaveValue("https://x.com/odoo");
    expect("tr:nth-child(2) input[type=checkbox]").toBeChecked();
    expect("tr:nth-child(3) input[type=text]").toHaveValue("https://fb.com/odoo");
    expect("tr:nth-child(3) input[type=checkbox]").not.toBeChecked();
    expect("tr:nth-child(4) input[type=text]").toHaveValue("https://www.example.com");

    expect(":iframe a:nth-of-type(1)").toHaveAttribute("href", "https://www.example.com/first");
    expect(":iframe a:nth-of-type(2)").toHaveAttribute("href", "/website/social/twitter");
    expect(":iframe a:nth-of-type(3)").toHaveAttribute("href", "https://www.example.com");

    await contains(".o-snippets-top-actions button.fa-undo").click();

    // fb link not in the dom should stay just after x link
    expect("tr:nth-child(1) input[type=text]").toHaveValue("https://x.com/odoo");
    expect("tr:nth-child(1) input[type=checkbox]").toBeChecked();
    expect("tr:nth-child(2) input[type=text]").toHaveValue("https://fb.com/odoo");
    expect("tr:nth-child(2) input[type=checkbox]").not.toBeChecked();
    expect("tr:nth-child(3) input[type=text]").toHaveValue("https://www.example.com/first");
    expect("tr:nth-child(4) input[type=text]").toHaveValue("https://www.example.com");

    expect(":iframe a:nth-of-type(1)").toHaveAttribute("href", "/website/social/twitter");
    expect(":iframe a:nth-of-type(2)").toHaveAttribute("href", "https://www.example.com/first");
    expect(":iframe a:nth-of-type(3)").toHaveAttribute("href", "https://www.example.com");
});

test("save social medias", async () => {
    onRpc("website", "read", ({ args }) => [
        { id: 1, social_facebook: "https://fb.com/odoo", social_twitter: "https://x.com/odoo" },
    ]);
    await setupWebsiteBuilder(`<div class="s_social_media"><h4>Social Media</h4></div>`);

    await click(":iframe h4");

    await contains("div[data-action-param='facebook'] input").edit("https://facebook.com/Odoo");

    let writeCalled = false;
    onRpc("website", "write", ({ args }) => {
        expect(args[0]).toEqual([1]);
        expect(args[1]).toInclude(["social_facebook", "https://facebook.com/Odoo"]);
        expect(args[1]).toInclude(["social_twitter", "https://x.com/odoo"]);
        writeCalled = true;
        return true;
    });
    onRpc("ir.ui.view", "save", ({ args }) => true);

    await contains(".o-snippets-top-actions button[data-action='save']").click();
    expect(writeCalled).toBe(true, { message: "did not write social links" });
});

test("social media snippet should not be user-selectable", async () => {
    await setupWebsiteBuilder(
        `<div class="s_social_media o_not_editable"><h4>Social Media</h4></div>`,
        { loadIframeBundles: true }
    );
    expect(":iframe .s_social_media").toHaveStyle({ "user-select": "none" });
});

test("share snippet should not be editable (except title) nor user-selectable", async () => {
    await setupWebsiteBuilder(
        `<div class="s_share">
            <h4 class="s_share_title">Share</h4>
            <a href="#"><i class="fa fa-facebook"/></a>
        </div>`,
        { loadIframeBundles: true }
    );
    expect(queryOne(":iframe .s_share").isContentEditable).toBe(false);
    expect(queryOne(":iframe .s_share_title").isContentEditable).toBe(true);
    expect(":iframe .s_share").toHaveStyle({ "user-select": "none" });
});

test("Edit share icon", async () => {
    const dragAndDropSnippet = async (dataSnippet) => {
        const dragUtils = await contains(
            `.o-snippets-menu #snippet_content .o_snippet_thumbnail[data-snippet='${dataSnippet}']`
        ).drag();
        await dragUtils.moveTo(":iframe .s_text_image .oe_drop_zone");
        await dragUtils.drop(getDragHelper());
        await waitForEndOfOperation();
    };
    await setupWebsiteBuilderWithSnippet("s_text_image", { loadIframeBundles: true });
    // Add a dummy snippet so that the page is dirty
    await dragAndDropSnippet("s_inline_text");
    await dragAndDropSnippet("s_share");
    await contains(":iframe .s_share a i").dblclick();
    expect(".modal-content").toBeDisplayed();
});
