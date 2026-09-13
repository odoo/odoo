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

// test("Call a style/class actions using the BuilderNumberSelect (UI behaviour)", async () => {
// });

// test("Call custom actions using the BuilderNumberSelect", async () => {
//     addBuilderOption({
//         selector: ".test-options-target",
//         template: xml`
//             <BuilderNumberSelect action="'itemAction'" inputAction="'inputAction'" inputActionParam="'numParam'">
//                 <BuilderSelectItem actionParam="'itemParam'" actionValue="'itemValue'">
//                     Select Item
//                 </BuilderSelectItem>
//             </BuilderNumberSelect>
//         `,
//     });

//     await setupHTMLBuilder(`
//         <div class="test-options-target">
//             Test options target
//         </div>
//     `);

//     await contains(":iframe .test-options-target").click();
//     expect(".o-hb-input-number").toHaveCount(1);
//     expect(".o-hb-number-select").not.toBeVisible();

//     await contains(".o-hb-input-number").click();
//     expect(".o-hb-select-dropdown").toBeVisible();

//     await contains(".o-hb-select-dropdown-item").click();
//     expect.verifySteps(["itemAction itemParam itemValue", "itemAction itemParam itemValue"]);
//     await animationFrame();
//     expect(".o-hb-number-select").toBeVisible();
//     expect(".o-hb-input-number").toHaveCount(0);

//     await contains(".o-hb-number-select").click();
//     await animationFrame();
//     expect(".o-hb-input-number").toHaveCount(1);
//     expect(".o-hb-number-select").not.toBeVisible();

//     await contains(".o-hb-input-number").edit(5);
//     expect.verifySteps(["inputAction numParam 5", "inputAction numParam 5"]);
// });
