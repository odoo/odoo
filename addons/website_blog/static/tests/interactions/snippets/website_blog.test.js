import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

setupInteractionWhiteList(["website_blog.website_blog"]);
describe.current.tags("interaction_dev");

test("click on next blog updates URL", async () => {
    const { core, el } = await startInteractions(`
        <section class="website_blog">
            <div id="o_wblog_next_container" style="width:100px; height: 100px;">
                <div class="o_record_cover_container h-100 o_wblog_post_page_cover o_wblog_post_page_cover_footer o_record_has_cover">
                    <a id="o_wblog_next_post_info" class="d-none" data-size="o_record_has_cover o_half_screen_height" data-url="/some/blog"></a>
                </div>
            </div>
        </section>
    `);
    expect(core.interactions.length).toBe(1);
    expect(browser.location.pathname).toBe("/")
    const nextBlogBtn = el.querySelector("#o_wblog_next_container");
    await click(nextBlogBtn);
    await advanceTime(300);
    expect(browser.location.pathname).toBe("/some/blog");
});
