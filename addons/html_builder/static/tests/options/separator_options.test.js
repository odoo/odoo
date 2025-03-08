import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("change width of separator", async () => {
    await setupWebsiteBuilder(`
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
