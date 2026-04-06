import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

class MailingList extends models.Model {
    name = fields.Char();
    is_public = fields.Boolean({ default: true });
    _records = [{ id: 1, name: "Newsletter List", is_public: true }];
}

defineWebsiteModels();
defineModels({ MailingList });

test("Options related to newsletter form should be at the form level", async () => {
    await setupWebsiteBuilderWithSnippet("s_newsletter_block");
    await contains(":iframe .s_newsletter_subscribe_form").click();
    expect("[data-container-title='Newsletter Form'] [data-label='On Success']").toHaveCount(1);
    // Unfold Newsletter Block option container
    await contains("[data-container-title='Newsletter Block'] button").click();
    // Verify option is not present at section level
    expect("[data-container-title='Newsletter Block'] [data-label='On Success']").toHaveCount(0);
    expect(":iframe .js_subscribe .js_subscribed_wrap p").toHaveClass("mb-0");
});
