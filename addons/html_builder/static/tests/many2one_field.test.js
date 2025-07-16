import { expect, test } from "@odoo/hoot";
import { setupHTMLBuilder } from "./helpers";

test("should prevent edition in many2one field", async () => {
    await setupHTMLBuilder(
        `<a data-oe-model="blog.post" data-oe-id="3" data-oe-field="blog_id" data-oe-type="many2one" data-oe-expression="blog_post.blog_id" data-oe-many2one-id="1" data-oe-many2one-model="blog.blog">
            Travel
        </a>`
    );
    expect(":iframe a").toHaveProperty("isContentEditable", false);
});
