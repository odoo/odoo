import { expect, test } from "@odoo/hoot";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { WebsiteBuilder } from "@html_builder/website_preview/website_builder_action";

defineWebsiteModels();

test("trigger mobile view", async () => {
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(".o_website_preview.o_is_mobile").toHaveCount(0);
    await contains("button[data-action='mobile']").click();
    expect(".o_website_preview.o_is_mobile").toHaveCount(1);
});

test("top window url in action context parameter", async () => {
    let websiteBuilder;
    patchWithCleanup(WebsiteBuilder.prototype, {
        setup() {
            websiteBuilder = this;
            this.props.action.context = {
                params: {
                    path: "/web/content/",
                },
            };
            super.setup();
        },
    });
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(websiteBuilder.initialUrl).toBe("/website/force/1?path=%2F");
});
