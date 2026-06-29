import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("Call a global BuilderSearchSelect action with params and a value", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ params: { mainParam: customParam }, value }) {
                expect.step(`customAction ${customParam} > ${value}`);
            }
        },
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect choices="[{ label: 'item_label_0', value: 'item_value_0' }]"
                    action="'customAction'"
                    actionParam="'param_0'"
                    actionValue="'value_0'"/>
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    await click(".popover [data-choice-index='0']");
    await animationFrame();
    // The `apply()` will be called twice: for preview and item selection.
    expect.verifySteps(["customAction param_0 > value_0", "customAction param_0 > value_0"]);
});
