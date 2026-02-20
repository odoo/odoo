import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addPlugin,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { BlogPageOptionPlugin } from "@website_blog/website_builder/blog_page_option_plugin";

defineWebsiteModels();

const testImgSrc = "/website_blog/static/src/img/cover_2.jpg";
test("Clicking on next post cover image does not activate the builder overlay", async () => {
    addPlugin(BlogPageOptionPlugin);
    await setupWebsiteBuilder(` 
        <main>
            <div id="o_wblog_post_main">Blog post content</div>
            <section id="o_wblog_post_footer">
                <div class="o_wblog_post_name">Post Name</div>
                <div class="o_wblog_post_subtitle">Post Subtitle</div>
                <div class="o_record_cover_image" style="background-image: url(${testImgSrc});">Cover</div>
            </section>
        </main>
    `);

    await contains(":iframe #o_wblog_post_footer .o_record_cover_image").click();
    expect(".oe_overlay").toHaveCount(0);
    expect(".options-container").toHaveCount(0);
    expect(":iframe #o_wblog_post_footer .o_wblog_post_name").toHaveAttribute(
        "contenteditable",
        "false"
    );
    expect(":iframe #o_wblog_post_footer .o_wblog_post_subtitle").toHaveAttribute(
        "contenteditable",
        "false"
    );
});
