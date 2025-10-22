import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { undo } from "@html_editor/../tests/_helpers/user_actions";
import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

describe.current.tags("desktop");

describe("replicate changes", () => {
    test("translated elements", async () => {
        const { getEditor } = await setupHTMLBuilder("", {
            headerContent: `
            <div class="test-1">
                <span data-oe-model="ir.ui.view" data-oe-id="600" data-oe-field="arch_db" data-oe-translation-state="translated" data-oe-translation-source-sha="4242">Contactez-nous</span>
            </div>
            <div class="test-2">
                <span data-oe-model="ir.ui.view" data-oe-id="600" data-oe-field="arch_db" data-oe-translation-state="translated" data-oe-translation-source-sha="4242">Contactez-nous</span>
            </div>
        `,
        });
        queryOne(":iframe .test-2 span").append(" ici");
        const editor = getEditor();
        editor.shared.history.addStep();
        expect(":iframe span:contains(Contactez-nous ici)").toHaveCount(2);
    });

    test("link and non-link elements", async () => {
        const { getEditor } = await setupHTMLBuilder(
            `
            <div class="test-4">
                <a data-oe-xpath="/t[1]/nav[1]/div[1]/div[1]/t[2]/ul[1]/li[2]/a[1]/" href="/blog/travel-1" data-oe-model="blog.blog" data-oe-id="1" data-oe-field="name" data-oe-type="char" data-oe-expression="nav_blog.name">Travel</a>
            </div>
            `,
            {
                headerContent: `
            <div class="test-1">
                <b data-oe-xpath="/t[1]/nav[1]/div[1]/ul[1]/li[3]/a[1]/b[1]" data-oe-model="blog.blog" data-oe-id="1" data-oe-field="name" data-oe-type="char" data-oe-expression="nav_blog.name">Travel</b>
            </div>
            <div class="test-2">
                <a data-oe-xpath="/t[1]/div[1]/div[1]/b[1]/a[1]" href="/blog/travel-1" data-oe-model="blog.post" data-oe-id="1" data-oe-field="blog_id" data-oe-type="many2one" data-oe-expression="blog_post.blog_id" data-oe-many2one-id="1" data-oe-many2one-model="blog.blog">Travel</a>
            </div>
            <div class="test-3">
                <span data-oe-xpath="/t[1]/nav[1]/div[1]/div[1]/t[2]/ul[1]/li[2]/a[1]/span[1]" data-oe-model="blog.blog" data-oe-id="1" data-oe-field="name" data-oe-type="char" data-oe-expression="nav_blog.name">Travel</span>
            </div>
        `,
            }
        );
        const editor = getEditor();
        queryOne(":iframe .test-1 b").append(" Abroad");
        editor.shared.history.addStep();
        expect(":iframe .test-1 b").toHaveText("Travel Abroad");
        expect(":iframe .test-2 a").toHaveText("Travel Abroad");
        expect(":iframe .test-3 span").toHaveText("Travel Abroad");
        expect(":iframe .test-4 a").toHaveInnerHTML("\u{FEFF}Travel Abroad\u{FEFF}"); // link in editable get feff

        queryOne(":iframe .test-4 a").append("!"); // the feff should not be forwarded
        editor.shared.history.addStep();
        expect(":iframe .test-1 b").toHaveText("Travel Abroad!");
        expect(":iframe .test-2 a").toHaveText("Travel Abroad!");
        expect(":iframe .test-3 span").toHaveText("Travel Abroad!");
        expect(":iframe .test-4 a").toHaveInnerHTML("\u{FEFF}Travel Abroad!\u{FEFF}");
    });

    test("menu items", async () => {
        const { getEditor } = await setupHTMLBuilder("", {
            headerContent: `
            <div class="test-1">
                <span data-oe-model="website.menu" data-oe-id="5" data-oe-field="name" data-oe-type="char" data-oe-expression="submenu.name">Home</span>
            </div>
            <div class="test-2">
                <span data-oe-model="website.menu" data-oe-id="5" data-oe-field="name" data-oe-type="char" data-oe-expression="submenu.name">Home</span>
            </div>
        `,
        });
        queryOne(":iframe .test-1 span").append("y");
        const editor = getEditor();
        editor.shared.history.addStep();
        expect(":iframe span:contains(Homey)").toHaveCount(2);
    });

    test("contact", async () => {
        const { getEditor } = await setupHTMLBuilder("", {
            headerContent: `
            <div class="test-1">
                <span data-oe-xpath="/t[1]/div[1]/div[2]/span[1]" data-oe-model="blog.post" data-oe-id="1" data-oe-field="author_id" data-oe-type="contact" data-oe-expression="blog_post.author_id" data-oe-many2one-id="3" data-oe-many2one-model="res.partner" data-oe-contact-options="{&quot;widget&quot;: &quot;contact&quot;, &quot;fields&quot;: [&quot;name&quot;], &quot;tagName&quot;: &quot;span&quot;, &quot;expression&quot;: &quot;blog_post.author_id&quot;, &quot;type&quot;: &quot;contact&quot;, &quot;inherit_branding&quot;: true, &quot;translate&quot;: false}">
                    <address class="o_portal_address mb-0">
                        <div>
                                <span itemprop="name">YourCompany, Mitchell Admin</span>
                        </div>
                        <div class="gap-2" itemscope="itemscope" itemtype="http://schema.org/PostalAddress">
                            <div itemprop="telephone"></div>
                        </div>
                    </address>
                </span>
            </div>
            <div class="test-2">
                <span data-oe-xpath="/t[1]/div[1]/div[2]/span[1]" data-oe-model="blog.post" data-oe-id="1" data-oe-field="author_id" data-oe-type="contact" data-oe-expression="blog_post.author_id" data-oe-many2one-id="3" data-oe-many2one-model="res.partner" data-oe-contact-options="{&quot;widget&quot;: &quot;contact&quot;, &quot;fields&quot;: [&quot;name&quot;], &quot;tagName&quot;: &quot;span&quot;, &quot;expression&quot;: &quot;blog_post.author_id&quot;, &quot;type&quot;: &quot;contact&quot;, &quot;inherit_branding&quot;: true, &quot;translate&quot;: false}">
                    <address class="o_portal_address mb-0">
                        <div>
                                <span itemprop="name">YourCompany, Mitchell Admin</span>
                        </div>
                        <div class="gap-2" itemscope="itemscope" itemtype="http://schema.org/PostalAddress">
                            <div itemprop="telephone"></div>
                        </div>
                    </address>
                </span>
            </div>
        `,
        });
        queryOne(":iframe .test-1 > *").append("changed");
        const editor = getEditor();
        editor.shared.history.addStep();
        expect(":iframe .test-1 > *").toHaveText(/changed/);
        expect(":iframe .test-2 > *").toHaveText(/changed/);
    });

    test("should not add o_dirty marks on the ones receiving the replicated changes", async () => {
        const { getEditor } = await setupHTMLBuilder("", {
            headerContent: `
            <div class="test-1">
                <span data-oe-model="ir.ui.view" data-oe-id="600" data-oe-field="arch_db" data-oe-translation-state="translated" data-oe-translation-source-sha="4242">Contactez-nous</span>
            </div>
            <div class="test-2">
                <span data-oe-model="ir.ui.view" data-oe-id="600" data-oe-field="arch_db" data-oe-translation-state="translated" data-oe-translation-source-sha="4242">Contactez-nous</span>
            </div>
            <div class="test-3">
                <span data-oe-model="ir.ui.view" data-oe-id="600" data-oe-field="arch_db" data-oe-translation-state="translated" data-oe-translation-source-sha="4242">Contactez-nous</span>
            </div>
        `,
        });
        const span1 = queryOne(":iframe .test-1 span");
        const span2 = queryOne(":iframe .test-2 span");
        const span3 = queryOne(":iframe .test-3 span");

        const editor = getEditor();
        span2.append(" ici");
        editor.shared.history.addStep();
        expect(span1).not.toHaveClass("o_dirty");
        expect(span2).toHaveClass("o_dirty");
        expect(span3).not.toHaveClass("o_dirty");
        expect([span1, span2, span3]).toHaveText("Contactez-nous ici");

        span1.append("!");
        editor.shared.history.addStep();
        expect(span1).toHaveClass("o_dirty");
        expect(span2).toHaveClass("o_dirty");
        expect(span3).not.toHaveClass("o_dirty");
        expect([span1, span2, span3]).toHaveText("Contactez-nous ici!");

        undo(editor);
        expect(span1).not.toHaveClass("o_dirty");
        expect(span2).toHaveClass("o_dirty");
        expect(span3).not.toHaveClass("o_dirty");
        expect([span1, span2, span3]).toHaveText("Contactez-nous ici");
    });

    test("changing several of occurences at the same time should converge to the same value", async () => {
        const { getEditor } = await setupHTMLBuilder("", {
            headerContent: `
            <div class="test-1">
                <span data-oe-model="ir.ui.view" data-oe-id="600" data-oe-field="arch_db" data-oe-translation-state="translated" data-oe-translation-source-sha="4242">Contactez-nous</span>
            </div>
            <div class="test-2">
                <span data-oe-model="ir.ui.view" data-oe-id="600" data-oe-field="arch_db" data-oe-translation-state="translated" data-oe-translation-source-sha="4242">Contactez-nous</span>
            </div>
            <div class="test-3">
                <span data-oe-model="ir.ui.view" data-oe-id="600" data-oe-field="arch_db" data-oe-translation-state="translated" data-oe-translation-source-sha="4242">Contactez-nous</span>
            </div>
        `,
        });
        const span1 = queryOne(":iframe .test-1 span");
        const span2 = queryOne(":iframe .test-2 span");
        const span3 = queryOne(":iframe .test-3 span");

        span2.append(" ici");
        span1.append("!");
        const editor = getEditor();
        editor.shared.history.addStep();
        expect(span1).toHaveClass("o_dirty");
        expect(span2).toHaveClass("o_dirty");
        expect(span3).not.toHaveClass("o_dirty");
        expect([span2, span3]).toHaveText(span1.textContent); // all the same text
    });
});
