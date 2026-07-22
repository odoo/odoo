import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("should not allow edition of date and datetime fields", async () => {
    await setupHTMLBuilder(
        `<time data-oe-model="blog.post" data-oe-id="3" data-oe-field="post_date" data-oe-type="datetime" data-oe-expression="blog_post.post_date" data-oe-original="2025-07-30 09:54:36" data-oe-original-with-format="07/30/2025 09:54:36" data-oe-original-tz="Europe/Brussels">
            Jul 30, 2025
        </time>`
    );
    expect(":iframe time").toHaveProperty("isContentEditable", false);
});

test("should allow changing datetime fields from the sidebar", async () => {
    await setupHTMLBuilder(
        `<time data-oe-model="blog.post" data-oe-id="3" data-oe-field="post_date" data-oe-type="datetime" data-oe-expression="blog_post.post_date" data-oe-original="2025-07-30 09:54:36" data-oe-original-with-format="07/30/2025 09:54:36" data-oe-original-tz="Europe/Brussels">
            Jul 30, 2025
        </time>`
    );
    await contains(":iframe time").click();
    expect("[data-action-id=fieldDateTime] input").toHaveValue("07/30/2025 09:54:36");
    await contains("[data-action-id=fieldDateTime] input").edit("09/22/2042 01:23:45");
    expect(":iframe time").toHaveText("09/22/2042 01:23:45");
});

test("should allow changing date fields from the sidebar", async () => {
    await setupHTMLBuilder(
        `<time data-oe-model="blog.post" data-oe-id="3" data-oe-field="post_date" data-oe-type="date" data-oe-expression="blog_post.post_date" data-oe-original="2025-07-30" data-oe-original-with-format="07/30/2025">
            Jul 30, 2025
        </time>`
    );
    await contains(":iframe time").click();
    expect("[data-action-id=fieldDateTime] input").toHaveValue("07/30/2025");
    await contains("[data-action-id=fieldDateTime] input").edit("09/22/2042");
    expect(":iframe time").toHaveText("09/22/2042");
});
