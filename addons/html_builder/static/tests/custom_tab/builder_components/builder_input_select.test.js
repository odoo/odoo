import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { expect, queryAll, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

const INPUT_SELECTOR = ".we-bg-options-container input";
const MENU_SELECTOR = ".o-dropdown--menu div[role='menuitem']";

function setupTestEnv() {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
            <BuilderInputSelectNumber styleAction="'width'" unit="'px'">
                <t t-foreach="['100px','75px','50px','25px','10px']" t-as="value" t-key="value">
                    <BuilderSelectItem styleActionValue="value" t-out="value"/>
                </t>
            </BuilderInputSelectNumber>`;
        }
    );
    return setupHTMLBuilder(
        `<div class="test-options-target" style="width: 100px;">Builder Input Select</div>`
    );
}

test("Click on Input should open/close dropdown", async () => {
    await setupTestEnv();
    await contains(":iframe .test-options-target").click();
    await contains(INPUT_SELECTOR).click();
    expect(queryAll(MENU_SELECTOR)).toHaveLength(5);
    await contains(INPUT_SELECTOR).click();
    expect(queryAll(MENU_SELECTOR)).toHaveLength(0);
});

test("Pressing Tab/Enter on Input should close dropdown", async () => {
    await setupTestEnv();
    await contains(":iframe .test-options-target").click();
    await contains(INPUT_SELECTOR).click();
    expect(queryAll(MENU_SELECTOR)).toHaveLength(5);
    await contains(INPUT_SELECTOR).press("Enter");
    expect(queryAll(MENU_SELECTOR)).toHaveLength(0);
    await contains(INPUT_SELECTOR).click();
    expect(queryAll(MENU_SELECTOR)).toHaveLength(5);
    await contains(INPUT_SELECTOR).press("Tab");
    expect(queryAll(MENU_SELECTOR)).toHaveLength(0);
});

test("Selecting dropdown value should update input and commit value", async () => {
    const { getEditableContent } = await setupTestEnv();
    await contains(":iframe .test-options-target").click();
    await contains(INPUT_SELECTOR).click();
    expect(INPUT_SELECTOR).toHaveValue(100);
    await contains(".o-dropdown--menu div[data-style-action-value='50px']").click();
    expect(INPUT_SELECTOR).toHaveValue(50);
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(
        `<div class="test-options-target" style="width: 50px;">Builder Input Select</div>`
    );
});

test("Manually inserting value in input should commit the value", async () => {
    const { getEditableContent } = await setupTestEnv();
    await contains(":iframe .test-options-target").click();
    const input = contains(INPUT_SELECTOR);
    expect(INPUT_SELECTOR).toHaveValue(100);
    await input.click();
    await input.edit("30");
    await input.press("Enter");
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(
        `<div class="test-options-target" style="width: 30px;">Builder Input Select</div>`
    );
});
