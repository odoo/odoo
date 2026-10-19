import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("change width of separator", async () => {
    await setupHTMLBuilder(`
            <div class="s_hr">
                <hr class="w-100">
            </div>
    `);
    await contains(":iframe .s_hr").click();
    await contains("div:contains('Width') button:contains('100%')").click();
    expect("[data-class-action='mx-auto']").toHaveCount(0);
    await contains(".o_popover [data-class-action='w-50']").click();
    expect("[data-class-action='mx-auto']").toHaveCount(1);
});
