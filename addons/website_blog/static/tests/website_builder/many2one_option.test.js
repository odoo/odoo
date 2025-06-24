import { Builder } from "@html_builder/builder";
import { startServer } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

class BlogBlog extends models.Model {
    _name = "blog.blog";
    name = fields.Char();
    website_id = fields.Many2one({ relation: "website" });
}
class BlogPost extends models.Model {
    _name = "blog.post";
    name = fields.Char();
    blog_id = fields.Many2one({ relation: "blog.blog" });
    recommended_next_post_id = fields.Many2one({ relation: "blog.post" });
    website_id = fields.Many2one({
        relation: "website",
        related: "blog_id.website_id",
    });
    is_published = fields.Boolean();
}
defineWebsiteModels();

/**
 * Generates HTML markup for a blog post with recommended next article section.
 *
 * @param {number} postId - ID of the blog post to render
 * @param {Object} pyEnv - Python environment containing blog post data
 * @returns {string} HTML markup for the blog post
 */
function getBlogPostMarkup(postId, pyEnv) {
    const post = pyEnv["blog.post"].read(postId)[0];
    const nextPostId = post.recommended_next_post_id;
    const nextPost = nextPostId ? pyEnv["blog.post"].read(nextPostId)[0] : null;

    return `
        <main>
            <section id="o_wblog_post_main">
                <div id="wrap" class="js_blog website_blog">
                    <div class="o_record_cover_container" data-res-model="blog.post" data-res-id="${
                        post.id
                    }">
                        <h1>${post.name}</h1>
                        ${
                            nextPost
                                ? `
                                <section id="o_wblog_post_footer" data-next-post-id="${nextPost.id}" data-is-next-post-recommended="True">
                                    ${nextPost.name}
                                </section>`
                                : ""
                        }
                    </div>
                </div>
            </section>
        </main>
    `;
}

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

test("Editing the recommended next post option updates recommended_next_post_id", async () => {
    defineModels([BlogBlog, BlogPost]);
    onRpc("/website/theme_customize_data_get", () => ["website_blog.opt_blog_post_read_next"]);
    onRpc("blog.post", "write", ({ args }) => {
        expect.step(`write ${args[1].recommended_next_post_id}`);
    });
    patchWithCleanup(Builder.prototype, {
        setup() {
            super.setup();
            this.editor.config.reloadEditor = () => {
                expect.step("reload");
            };
        },
    });

    const pyEnv = await startServer();
    const websiteId = pyEnv["website"].create({});
    const blogId = pyEnv["blog.blog"].create({ name: "Blog Test", website_id: websiteId });
    const blogData = { blog_id: blogId, is_published: true };
    const [post1, post2, post3] = pyEnv["blog.post"].create([
        { name: "Post 1", ...blogData },
        { name: "Post 2", ...blogData },
        { name: "Post 3", ...blogData },
    ]);
    pyEnv["blog.post"].write(post3, { recommended_next_post_id: post1 });

    mockService("website", {
        get currentWebsite() {
            return {
                id: websiteId,
                default_lang_id: { code: "en_US" },
                metadata: {
                    mainObject: { id: post3, model: "blog.post" },
                },
            };
        },
    });

    await setupWebsiteBuilder(getBlogPostMarkup(post3, pyEnv), { hasToCreateWebsite: false });

    await contains("[data-name='customize']").click();
    await contains("[data-label='Recommended Post'] .o_select_menu_toggler").click();
    await contains(".o-dropdown-item:contains('Post 2')").click();
    expect.verifySteps([`write ${post2}`, "reload"]);

    await contains(".o-hb-btn[aria-label='Unselect']").click();
    expect.verifySteps([`write ${false}`, "reload"]);
});
