import { test, expect } from "@odoo/hoot";
import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-dom";

test("Empty BuilderNumberSelect should act as a BuilderNumberInput", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderNumberSelect inputAction="'styleAction'" inputActionParam="'padding'" unit="'px'">
                    <t t-foreach="[]" t-as="column" t-key="column_index">
                        <BuilderSelectItem classAction="column" t-out="column"/>
                    </t>
                </BuilderNumberSelect>
            </BuilderRow>
        `,
    });

    await setupHTMLBuilder(`
        <div class="test-options-target">Content...</div>
    `);

    await contains(":iframe .test-options-target").click();
    expect(".o-hb-number-select-toggle").toHaveCount(0);
    expect(".o-hb-input-field-number").toHaveCount(1);

    await contains(".o-hb-input-number").edit(15);
    expect(":iframe .test-options-target").toHaveStyle({ padding: "15px" });
});

test("Call a style/class actions using the BuilderNumberSelect (UI behaviour)", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderNumberSelect action="'classAction'"
                    inputAction="'styleAction'"
                    inputActionParam="'padding'"
                    unit="'px'"
                    min="0">
                    <BuilderSelectItem actionParam="'class-1'">Option 1</BuilderSelectItem>
                    <BuilderSelectItem actionParam="'class-2'">Option 2</BuilderSelectItem>
                </BuilderNumberSelect>
            </BuilderRow>
        `,
    });

    await setupHTMLBuilder(`
        <div class="test-options-target class-2">Content...</div>
    `);

    await contains(":iframe .test-options-target").click();
    expect("div.o-hb-input-field-number").toHaveCount(0);
    expect("input.o-hb-input-field-number").toHaveCount(1);

    await contains("input.o-hb-input-field-number").click();
    expect(".o-hb-select-dropdown").toBeVisible();

    await contains(".o-hb-select-dropdown-item:contains('Option 1')").click();
    expect(":iframe .test-options-target").toHaveClass("class-1");
    await animationFrame();
    expect("input.o-hb-input-field-number").toHaveValue("Option 1");
    // expect(".o-hb-input-number").toHaveCount(0);

    // await contains(".o-hb-number-select").click();
    // await animationFrame();
    // expect(".o-hb-input-number").toHaveCount(1);
    // expect(".o-hb-number-select").not.toBeVisible();

    // await contains(".o-hb-input-number").edit(5);
    // expect.verifySteps(["inputAction numParam 5", "inputAction numParam 5"]);
});
