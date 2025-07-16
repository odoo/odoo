import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { queryOne } from "@odoo/hoot-dom";

defineWebsiteModels();

test.tags("desktop");
test("should prevent edition in many2one field", async () => {
    await setupWebsiteBuilder(
        `<a data-oe-model="blog.post" data-oe-id="3" data-oe-field="blog_id" data-oe-type="many2one" data-oe-expression="blog_post.blog_id" data-oe-many2one-id="1" data-oe-many2one-model="blog.blog">
            Travel
        </a>`
    );
    expect(queryOne(":iframe a").isContentEditable).toBe(false);
});
