import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { addBuilderOption } from "@html_builder/../tests/helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";

defineWebsiteModels();

test("switch to custom tab and click on a main page option", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = "main";
            static template = xml`<BuilderButton classAction="'my-custom-class'"/>`;
        }
    );
    await setupWebsiteBuilder(`<main>b</main>`);
    await contains('[id="customize-tab"]').click();
    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container").toBeDisplayed();
    expect("[data-class-action='my-custom-class']").toHaveCount(1);
    expect(":iframe main").toHaveClass("my-custom-class");
});
