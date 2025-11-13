import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame, press } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("should prevent edition in many2one field", async () => {
    await setupHTMLBuilder(
        `<a data-oe-model="blog.post" data-oe-id="3" data-oe-field="blog_id" data-oe-type="many2one" data-oe-expression="blog_post.blog_id" data-oe-many2one-id="1" data-oe-many2one-model="blog.blog">
            Travel
        </a>`
    );
    expect(":iframe a").toHaveProperty("isContentEditable", false);
});

test.tags("desktop"); // NavigationItem only react to mouvemove which is not triggered in test for mobile
test("Preview changes of many2one option", async () => {
    onRpc(
        "ir.qweb.field.contact",
        "get_record_to_html",
        ({ args: [[id]], kwargs }) => `<span>The ${kwargs.options.option} of ${id}</span>`
    );

    await setupHTMLBuilder(`
        <div>
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
    await contains("span.o-dropdown-item.dropdown-item").hover();
    expect(":iframe span.span-1 > span").toHaveText("The Name of 1");
    expect(":iframe span.span-2 > span").toHaveText("The Address of 1");
    expect(":iframe span.span-3 > span").toHaveText("The Address of 3"); // author of other post is not changed
    expect(":iframe span.span-4").toHaveText("Hermit");

    await press("esc"); // This causes the dropdown to close, and thus the preview to be reverted
    await animationFrame();
    expect(":iframe span.span-1 > span").toHaveText("The Name of 3");
    expect(":iframe span.span-2 > span").toHaveText("The Address of 3");
    expect(":iframe span.span-4").toHaveText("Other");
});

test("Many2OneOption: add null_text option in dropdown", async () => {
    onRpc(
        "ir.qweb.field.contact",
        "get_record_to_html",
        ({ args: [[id]], kwargs }) => `<span>The ${kwargs.options.option} of ${id}</span>`
    );
    await setupHTMLBuilder(`
        <div class="many2oneoption_dropdown"
            data-oe-many2one-id="1"
            data-oe-many2one-model="res.partner"
            data-oe-contact-options='{"null_text":"Remote"}'>
            <span>location</span>
        </div>
    `);
    await contains(":iframe .many2oneoption_dropdown").click();
    expect("button.btn.dropdown").toHaveCount(1);
    await contains("button.btn.dropdown").click();
    await contains("span.o-dropdown-item.dropdown-item:contains('Remote')").click();
    expect(":iframe div.many2oneoption_dropdown").toHaveText("Remote");
});
