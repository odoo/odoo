import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

setupInteractionWhiteList(["website_blog.toc"]);
describe.current.tags("interaction_dev");

const blogPostTemplate = `
    <div id="o_wblog_post_main">
        <div class="o_wblog_toc"><nav class="o_wblog_toc_nav"></nav></div>
        <div class="o_wblog_toc o_wblog_toc_mobile"><nav class="o_wblog_toc_nav"></nav></div>
        <div id="o_wblog_post_content">
            <div class="o_wblog_post_content_field">
                <h2>First</h2>
                <div style="height: 1000px;"></div>
                <h2>Second</h2>
                <div style="height: 1000px;"></div>
                <h2>Third</h2>
                <div style="height: 1000px;"></div>
            </div>
        </div>
    </div>
`;

test("table of contents lists the headings", async () => {
    const { core } = await startInteractions(blogPostTemplate);
    expect(core.interactions).toHaveLength(1);
    expect(".o_wblog_toc:not(.o_wblog_toc_mobile) .o_wblog_toc_link").toHaveCount(3);
    expect(".o_wblog_toc_mobile .o_wblog_toc_link").toHaveCount(3);
    expect(".o_wblog_toc:not(.o_wblog_toc_mobile) .o_wblog_toc_link.active").toHaveText("First");
});

test("table of contents follows the window scroll", async () => {
    let scrollY = 0;
    patchWithCleanup(window, {
        get scrollY() {
            return scrollY;
        },
    });
    await startInteractions(blogPostTemplate);
    const activeLinkSelector = ".o_wblog_toc:not(.o_wblog_toc_mobile) .o_wblog_toc_link.active";
    expect(activeLinkSelector).toHaveText("First");

    scrollY = queryOne("#blog_table_of_content_2").getBoundingClientRect().top;
    window.dispatchEvent(new Event("scroll"));
    expect(activeLinkSelector).toHaveText("Second");

    scrollY = queryOne("#blog_table_of_content_3").getBoundingClientRect().top;
    window.dispatchEvent(new Event("scroll"));
    expect(activeLinkSelector).toHaveText("Third");
});
