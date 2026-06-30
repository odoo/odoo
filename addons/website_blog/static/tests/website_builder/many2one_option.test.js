import { expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Change contact oe-many2one-id of a blog author changes other instance of same contact and avatar", async () => {
    onRpc(
        "ir.qweb.field.contact",
        "get_record_to_html",
        ({ args: [[id]], kwargs }) => `<span>The ${kwargs.options.option} of ${id}</span>`
    );

    await setupWebsiteBuilder(`
        <div>
            <div data-oe-model="blog.post" data-oe-id="3" data-oe-field="author_avatar">
                <img src="/web/image/res.partner/3/avatar_1024">
            </div>
            <span class="span-1" data-oe-model="blog.post" data-oe-id="3" data-oe-field="author_id" data-oe-type="contact" data-oe-many2one-id="3" data-oe-many2one-model="res.partner" data-oe-contact-options='{"option": "Name"}'>
                <span>The Name of 3</span>
            </span>
            <span class="span-2" data-oe-model="blog.post" data-oe-id="3" data-oe-field="author_id" data-oe-type="contact" data-oe-many2one-id="3" data-oe-many2one-model="res.partner" data-oe-contact-options='{"option": "Address"}'>
                <span>The Address of 3</span>
            </span>
            <span class="span-3" data-oe-model="blog.post" data-oe-id="6" data-oe-field="author_id" data-oe-type="contact" data-oe-many2one-id="3" data-oe-many2one-model="res.partner" data-oe-contact-options='{"option": "Address"}'>
                <span>The Address of 3</span>
            </span>
            <span class="span-4" data-oe-model="blog.post" data-oe-id="3" data-oe-field="author_id" data-oe-type="other" data-oe-many2one-id="3" data-oe-many2one-model="res.partner">Other</span>
        <div>
    `);

    await contains(":iframe .span-1").click();
    expect("button.btn.dropdown").toHaveCount(1);
    await contains("button.btn.dropdown").click();
    await contains("span.o-dropdown-item.dropdown-item").click();
    expect(":iframe span.span-1 > span").toHaveText("The Name of 1");
    expect(":iframe span.span-2 > span").toHaveText("The Address of 1");
    expect(":iframe span.span-3 > span").toHaveText("The Address of 3"); // author of other post is not changed
    expect(":iframe span.span-4").toHaveText("Hermit");
    expect(":iframe div > img").toHaveAttribute("src", "/web/image/res.partner/1/avatar_1024");
});
