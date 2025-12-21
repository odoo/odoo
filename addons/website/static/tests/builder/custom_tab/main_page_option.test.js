import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("switch to custom tab and click on a main page option", async () => {
    addOption({
        selector: "main",
        template: xml`<BuilderButton classAction="'my-custom-class'"/>`,
    });
    await setupWebsiteBuilder(`<main>b</main>`);
    await contains('[id="customize-tab"]').click();
    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container").toBeDisplayed();
    expect("[data-class-action='my-custom-class']").toHaveCount(1);
    expect(":iframe main").toHaveClass("my-custom-class");
});
