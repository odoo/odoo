import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./helpers";

defineWebsiteModels();

test("trigger mobile view", async () => {
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(".o_website_preview.o_is_mobile").toHaveCount(0);
    await contains("button[data-action='mobile']").click();
    expect(".o_website_preview.o_is_mobile").toHaveCount(1);
});
