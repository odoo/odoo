import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

const TARGET = `<div class="test-options-target" data-name="Target">Target</div>`;

function addSizeOption() {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label="'Size'">
                <BuilderButtonGroup>
                    <BuilderButton classAction="'small'">Small</BuilderButton>
                    <BuilderButton classAction="'large'">Large</BuilderButton>
                </BuilderButtonGroup>
                <t t-set-slot="collapse">
                    <BuilderRow level="1" label="'Shown'">
                        <BuilderCheckbox classAction="'shown'"/>
                    </BuilderRow>
                </t>
            </BuilderRow>`,
    });
}

/**
 * `showAllOptions` waits for the sidebar to render, which only happens when
 * the mocked animation frames advance.
 */
async function showAllOptions(builderOptions, target) {
    let settled = false;
    const promise = builderOptions.showAllOptions(target).finally(() => (settled = true));
    while (!settled) {
        await animationFrame();
    }
    return promise;
}

test("lists the controls of the sidebar and commits one", async () => {
    addSizeOption();
    const { getEditor } = await setupHTMLBuilder(TARGET);
    const { builderOptions } = getEditor().shared;
    await contains(":iframe .test-options-target").click();

    const [{ title, rows }] = builderOptions.getOptionControls();

    expect(title).toBe("Target");
    expect(rows.map((row) => row.label)).toEqual(["Size"]);
    const [group] = rows[0].controls;
    expect(group.kind).toBe("choice");
    const [small, large] = group.getChoices();
    expect([small.getLabel(), large.getLabel()]).toEqual(["Small", "Large"]);

    large.commit();
    await animationFrame();

    expect(":iframe .test-options-target").toHaveClass("large");
    expect(large.isActive()).toBe(true);
});

test("shows the options of the collapsed rows", async () => {
    addSizeOption();
    const { getEditor } = await setupHTMLBuilder(TARGET);
    const { builderOptions } = getEditor().shared;

    const hasOptions = await showAllOptions(
        builderOptions,
        queryOne(":iframe .test-options-target")
    );

    expect(hasOptions).toBe(true);
    const [{ rows }] = builderOptions.getOptionControls();
    expect(rows.map((row) => row.label)).toEqual(["Size", "Shown"]);
    expect(rows[1].controls.map((control) => control.kind)).toEqual(["toggle"]);
});

test("shows the options when the sidebar is on another tab", async () => {
    addSizeOption();
    const { getEditor } = await setupHTMLBuilder(TARGET);
    const { builderOptions } = getEditor().shared;
    await contains(":iframe .test-options-target").click();
    expect(".o_customize_tab").toHaveCount(1);
    await contains("#blocks-tab").click();
    expect(".o_customize_tab").toHaveCount(0);

    await showAllOptions(builderOptions, queryOne(":iframe .test-options-target"));

    expect(".o_customize_tab").toHaveCount(1);
    expect(builderOptions.getOptionControls()[0].rows).toHaveLength(2);
});
