import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

const CUSTOM_VALUE_INPUT = "div.o-hb-input-field-number";
const SELECT_LABEL_INPUT = "input.o-hb-input-field-number";

describe.current.tags("desktop");

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

    const { waitSidebarUpdated } = await setupHTMLBuilder(`
        <div class="test-options-target">Content...</div>
    `);

    await contains(":iframe .test-options-target").click();
    await waitSidebarUpdated();
    expect(CUSTOM_VALUE_INPUT).toHaveCount(1);
    expect(SELECT_LABEL_INPUT).toHaveCount(0);

    // Clicking the input must not open an empty dropdown.
    await contains(".o-hb-input-number").click();
    await animationFrame();
    expect(".o-hb-select-dropdown").toHaveCount(0);

    await contains(".o-hb-input-number").edit(15);
    await waitSidebarUpdated();
    expect(":iframe .test-options-target").toHaveStyle({ padding: "15px" });
});

test("Call actions using the BuilderNumberSelect (UI behaviour)", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderNumberSelect action="'classAction'"
                    inputAction="'styleAction'"
                    inputActionParam="'padding'"
                    unit="'px'"
                    min="0">
                    <BuilderSelectItem actionParam="'p-1'">Padding 1</BuilderSelectItem>
                    <BuilderSelectItem actionParam="'p-2'">Padding 2</BuilderSelectItem>
                </BuilderNumberSelect>
            </BuilderRow>
        `,
    });

    const { waitSidebarUpdated } = await setupHTMLBuilder(`
        <div class="test-options-target" style="padding: 10px;">Content...</div>
    `);

    await contains(":iframe .test-options-target").click();
    await waitSidebarUpdated();
    expect(CUSTOM_VALUE_INPUT).toHaveCount(1);
    expect(SELECT_LABEL_INPUT).toHaveCount(0);

    await contains(CUSTOM_VALUE_INPUT).click();
    await animationFrame();
    expect(".o-hb-select-dropdown").toHaveCount(1);
    await contains(".o-hb-select-dropdown-item:contains('Padding 1')").click();
    await waitSidebarUpdated();
    expect(SELECT_LABEL_INPUT).toHaveValue("Padding 1");
    expect(".o-hb-select-dropdown").toHaveCount(0);
    expect(":iframe .test-options-target").toHaveClass("p-1");
    expect(":iframe .test-options-target").not.toHaveStyle("padding", { inline: true });

    // Clicking the label switches it to the input field and opens the dropdown.
    await contains(SELECT_LABEL_INPUT).click();
    await animationFrame();
    expect(CUSTOM_VALUE_INPUT).toHaveCount(1);
    expect(SELECT_LABEL_INPUT).toHaveCount(0);
    expect(".o-hb-select-dropdown").toHaveCount(1);

    // Editing the input field applies the new custom style and removes the
    // previous class.
    await contains(`${CUSTOM_VALUE_INPUT} input`).edit(5);
    await waitSidebarUpdated();
    expect(":iframe .test-options-target").toHaveStyle({ padding: "5px" });
    expect(":iframe .test-options-target").not.toHaveClass("p-1");

    // Clicking anywhere outside hides the dropdown while keeping the custom
    // input field visible.
    await contains(".hb-row-label").click();
    await animationFrame();
    expect(CUSTOM_VALUE_INPUT).toHaveCount(1);
    expect(SELECT_LABEL_INPUT).toHaveCount(0);
    expect(".o-hb-select-dropdown").toHaveCount(0);

    // Clicking away with a selected item shows the selection label again
    // instead of the current custom input.
    await contains(CUSTOM_VALUE_INPUT).click();
    await contains(".o-hb-select-dropdown-item:contains('Padding 2')").click();
    await waitSidebarUpdated();
    await contains(SELECT_LABEL_INPUT).click();
    await animationFrame();
    expect(CUSTOM_VALUE_INPUT).toHaveCount(1);
    expect(SELECT_LABEL_INPUT).toHaveCount(0);
    await contains(".hb-row-label").click();
    await animationFrame();
    expect(CUSTOM_VALUE_INPUT).toHaveCount(0);
    expect(SELECT_LABEL_INPUT).toHaveCount(1);
});

test("clean the input action and the selected item's action and shorthand", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderNumberSelect action="'attributeAction'"
                inputAction="'styleAction'" inputActionParam="'padding'"
                unit="'px'">
                <BuilderSelectItem actionParam="'data-custom-first'" actionValue="'first'"
                    classAction="'first-preset'">
                    First
                </BuilderSelectItem>
            </BuilderNumberSelect>
        `,
    });
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `<div class="test-options-target" style="padding: 5px;">Content...</div>`
    );
    await contains(":iframe .test-options-target").click();
    await waitSidebarUpdated();

    // Selecting the preset removes the custom padding and adds its attribute and class.
    await contains(CUSTOM_VALUE_INPUT).click();
    await contains(".o-hb-select-dropdown-item:contains('First')").click();
    await waitSidebarUpdated();
    expect(":iframe .test-options-target").not.toHaveStyle("padding", { inline: true });
    expect(":iframe .test-options-target").toHaveAttribute("data-custom-first", "first");
    expect(":iframe .test-options-target").toHaveClass("first-preset");

    // Entering a custom value applies padding and removes the preset's attribute and class.
    await contains(SELECT_LABEL_INPUT).click();
    await contains(`${CUSTOM_VALUE_INPUT} input`).edit(15);
    await waitSidebarUpdated();
    expect(":iframe .test-options-target").toHaveStyle({ padding: "15px" });
    expect(":iframe .test-options-target").not.toHaveAttribute("data-custom-first");
    expect(":iframe .test-options-target").not.toHaveClass("first-preset");
});

test("use a shorthand action without inputAction", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderNumberSelect styleAction="'padding'" unit="'px'" preview="false">
                <BuilderSelectItem styleActionValue="'10px'">First</BuilderSelectItem>
            </BuilderNumberSelect>
        `,
    });
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `<div class="test-options-target" style="padding: 5px;">Content...</div>`
    );
    await contains(":iframe .test-options-target").click();
    await waitSidebarUpdated();

    // Selecting the preset applies its padding and displays its label.
    await contains(CUSTOM_VALUE_INPUT).click();
    await contains(".o-hb-select-dropdown-item:contains('First')").click();
    await waitSidebarUpdated();
    expect(":iframe .test-options-target").toHaveStyle({ padding: "10px" });
    expect(SELECT_LABEL_INPUT).toHaveValue("First");

    // Editing the input uses the shorthand action to apply the padding.
    await contains(SELECT_LABEL_INPUT).click();
    await contains(`${CUSTOM_VALUE_INPUT} input`).edit(15);
    await waitSidebarUpdated();
    expect(":iframe .test-options-target").toHaveStyle({ padding: "15px" });
});
