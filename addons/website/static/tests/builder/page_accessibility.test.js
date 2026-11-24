import { expect, queryAllTexts, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

test("page check highlights images without alt text and heading issues", async () => {
    await setupWebsiteBuilder(`
        <main>
            <section>
                <h2>Title</h2>
                <h4>Subtitle</h4>
                <h3><br></h3>
                <img src="/web/static/img/placeholder.png" width="50" height="50">
                <img src="/web/static/img/placeholder.png" width="50" height="50" alt="">
            </section>
        </main>
    `);

    await contains("button[aria-label='Highlight accessibility issues']").click();
    expect(queryAllTexts(":iframe [data-page-accessibility-overlay]")).toEqual([
        "Missing alt text",
        "H4 after H2",
        "Empty heading",
    ]);
    expect(".o_notification_content").toHaveText(
        "1 image(s) have no alt text. 1 heading(s) are empty. 1 heading(s) skip a level."
    );

    await contains("button[aria-label='Clear 3 accessibility highlight(s)']").click();
    expect(":iframe [data-page-accessibility-overlay]").toHaveCount(0);
});
