import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { expect, test, describe } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("should pass the context", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ params: { mainParam: testParam }, value }) {
                expect.step(`customAction ${testParam} ${value}`);
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
            <BuilderContext action="'customAction'" actionParam="'myParam'">
                <BuilderButton actionValue="'myValue'">MyAction</BuilderButton>
            </BuilderContext>
        `;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container button").click();
    // The function `apply` should be called twice (on hover (for preview), then, on click).
    expect.verifySteps(["customAction myParam myValue", "customAction myParam myValue"]);
});
