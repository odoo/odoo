import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "../../website_helpers";
import { BuilderAction } from "@html_builder/core/builder_action";

defineWebsiteModels();

test("should pass the context", async () => {
    addActionOption({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ params: { mainParam: testParam }, value }) {
                expect.step(`customAction ${testParam} ${value}`);
            }
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderContext action="'customAction'" actionParam="'myParam'">
                <BuilderButton actionValue="'myValue'">MyAction</BuilderButton>
            </BuilderContext>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container button").click();
    // The function `apply` should be called twice (on hover (for preview), then, on click).
    expect.verifySteps(["customAction myParam myValue", "customAction myParam myValue"]);
});
