import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

test("should not allow edition of date and datetime fields", async () => {
    await setupWebsiteBuilder(
        `<time data-oe-model="blog.post" data-oe-id="3" data-oe-field="post_date" data-oe-type="datetime" data-oe-expression="blog_post.post_date" data-oe-original="2025-07-30 09:54:36" data-oe-original-with-format="07/30/2025 09:54:36" data-oe-original-tz="Europe/Brussels">
            Jul 30, 2025
        </time>`
    );
    expect(":iframe time").toHaveProperty("isContentEditable", false);
});
