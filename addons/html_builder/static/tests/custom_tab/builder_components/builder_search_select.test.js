import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { expect, test, describe, before, getFixture } from "@odoo/hoot";
import { animationFrame, click, press, waitForNone, queryAllTexts } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("Call a global BuilderSearchSelect action with params", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ params: { mainParam: param }, value }) {
                expect.step(`customAction: ${param} > ${value}`);
            }
        },
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect choices="[{ label: 'Option 0', props: { actionValue: 'value_0' } }]"
                    action="'customAction'"
                    actionParam="'param_0'"/>
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
    expect.verifySteps(["customAction: param_0 > value_0", "customAction: param_0 > value_0"]);
});

test("The BuilderSearchSelect item action takes precedence over the parent one", async () => {
    addBuilderAction({
        sizeAction: class extends BuilderAction {
            static id = "sizeAction";
            apply() {
                expect.step("size action");
            }
        },
        colorAction: class extends BuilderAction {
            static id = "colorAction";
            apply() {
                expect.step("color action");
            }
        },
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect choices="[
                        {
                            label: 'Option 0',
                            props: {
                                action: 'colorAction',
                                classAction: 'class_0',
                            }
                        },
                        {
                            label: 'Option 1',
                            props: {
                                classAction: 'class_1',
                            }
                        },
                    ]"
                    action="'sizeAction'"/>
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
    expect.verifySteps(["color action", "color action"]);

    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    await click(".popover [data-choice-index='1']");
    await animationFrame();
    expect.verifySteps(["size action", "size action"]);
});

test("Call different BuilderSearchSelect item actions", async () => {
    addBuilderAction({
        sizeAction: class extends BuilderAction {
            static id = "sizeAction";
            apply({ params }) {
                expect.step(`size: ${params.H}/${params.W}`);
            }
        },
        colorAction: class extends BuilderAction {
            static id = "colorAction";
            apply({ value }) {
                expect.step(`color: ${value}`);
            }
        },
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect choices="[
                        {
                            label: 'Option 0',
                            props: {
                                action: 'sizeAction',
                                actionParam: { H: 50, W: 75 },
                                styleAction: 'opacity',
                                styleActionValue: '0.5',
                            }
                        },
                        {
                            label: 'Option 1',
                            props: {
                                action: 'colorAction',
                                styleAction: 'opacity',
                                styleActionValue: '0.75',
                                actionValue: 'Green',
                            }
                        },
                    ]"
                />
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
    expect.verifySteps(["size: 50/75", "size: 50/75"]);
    expect(":iframe .test-options-target").toHaveStyle({ opacity: "0.5" });

    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    await click(".popover [data-choice-index='1']");
    await animationFrame();
    expect.verifySteps(["color: Green", "color: Green"]);
    expect(":iframe .test-options-target").toHaveStyle({ opacity: "0.75" });
});

test("Call a filtered BuilderSearchSelect item action", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect choices="[
                        {
                            label: 'Option 0',
                            props: {
                                styleAction: 'opacity',
                                styleActionValue: '0',
                            }
                        },
                        {
                            label: 'Option 1',
                            props: {
                                styleAction: 'opacity',
                                styleActionValue: '1',
                            }
                        },
                    ]"
                />
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    await press("0");
    await waitForNone(".popover [data-choice-index='1']", { timeout: 500 });
    await click(".popover [data-choice-index='0']");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveStyle({ opacity: "0" });
});

test("Call a combination of BuilderSearchSelect and BuilderSearchSelect item actions (groups)", async () => {
    addBuilderAction({
        shapeAction: class extends BuilderAction {
            static id = "shapeAction";
            apply({ params: { mainParam: dimensions } }) {
                expect.step(`shape: ${dimensions}`);
            }
        },
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect styleAction="'opacity'" action="'shapeAction'" actionParam="'2D'" groups="[
                        {
                            label: 'Group 0',
                            choices: [
                                {
                                    label: 'Group 0 > Option 0',
                                    props: {
                                        classAction: '',
                                        styleActionValue: '0',
                                    }
                                },
                                {
                                    label: 'Group 0 > Option 1',
                                    props: {
                                        classAction: 'class_0',
                                        styleActionValue: '0.5',
                                    }
                                }
                            ],
                        },
                        {
                            label: 'Group 1',
                            choices: [
                                {
                                    label: 'Group 1 > Option 0',
                                    props: {
                                        classAction: 'class_1',
                                        styleActionValue: '1',
                                    }
                                }
                            ],
                        },
                    ]"
                />
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();

    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    await click(".popover [data-choice-index='1']");
    await animationFrame();
    expect.verifySteps(["shape: 2D", "shape: 2D"]);
    expect(":iframe .test-options-target").toHaveStyle({ opacity: "0" });

    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    await click(".popover [data-choice-index='2']");
    await animationFrame();
    expect.verifySteps(["shape: 2D", "shape: 2D"]);
    expect(":iframe .test-options-target").toHaveStyle({ opacity: "0.5" });
    expect(":iframe .test-options-target").toHaveClass("class_0");

    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    await click(".popover [data-choice-index='4']");
    await animationFrame();
    expect.verifySteps(["shape: 2D", "shape: 2D"]);
    expect(":iframe .test-options-target").toHaveStyle({ opacity: "1" });
    expect(":iframe .test-options-target").toHaveClass("class_1");
});

test("Use isActiveItem for an option in the BuilderSearchSelect", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect choices="[
                        {
                            label: 'Option 0',
                            props: {
                                classAction: 'class_0',
                            }
                        },
                        {
                            label: 'Option 1',
                            props: {
                                id: 'opt_1',
                                classAction: 'class_1',
                            }
                        },
                    ]"
                />
                <div class="dependency" t-if="this.isActiveItem('opt_1')">Dependency...</div>
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target class_0">Content...</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(1);
    expect("[data-label='Test'] .dropdown-toggle").toHaveText("Option 0");
    expect(".dependency").toHaveCount(0);

    await contains("[data-label='Test'] .dropdown-toggle").click();
    expect(".o-dropdown-item:visible").toHaveCount(2);
    await contains("[data-choice-index='1']").click();
    expect(".dependency").toHaveCount(1);
});

test("Consider the priority of BuilderSearchSelect items", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect choices="[
                        {
                            label: 'None',
                            props: {
                                classAction: '',
                            }
                        },
                        {
                            label: 'Style 1',
                            props: {
                                classAction: 'class_1',
                            }
                        },
                        {
                            label: 'Style 2',
                            props: {
                                classAction: 'class_2 class_3',
                            }
                        },
                    ]"
                />
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target class_1">Content...</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect("[data-label='Test'] .dropdown-toggle").toHaveText("Style 1");

    await contains("[data-label='Test'] .dropdown-toggle").click();
    await contains(".o-overlay-item [data-choice-index='0']").click();
    expect("[data-label='Test'] .dropdown-toggle").toHaveText("None");

    await contains("[data-label='Test'] .dropdown-toggle").click();
    await contains(".o-overlay-item [data-choice-index='2']").click();
    expect("[data-label='Test'] .dropdown-toggle").toHaveText("Style 2");
});

test("The applyTo feature is changing the BuilderSearchSelect visibility", async () => {
    addBuilderOption({
        selector: ".parent-options-target",
        template: xml`
            <BuilderRow label.translate="Test 0">
                <BuilderButton applyTo="'.child-options-target'" classAction="'class_apply_to'"/>
            </BuilderRow>
            <BuilderRow label.translate="Test 1">
                <BuilderSearchSelect applyTo="'.class_apply_to'" choices="[
                        {
                            label: 'Option 0',
                            props: {
                                classAction: 'class_0',
                            }
                        },
                        {
                            label: 'Option 1',
                            props: {
                                classAction: 'class_1',
                            }
                        },
                    ]"
                />
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(
        `<div class="parent-options-target"><div class="child-options-target class_1">Content...</div></div>`
    );
    await contains(":iframe .parent-options-target").click();
    expect("[data-class-action='class_apply_to']").not.toHaveClass("active");
    expect(".options-container button.dropdown-toggle").toHaveCount(0);
    await contains("[data-class-action='class_apply_to']").click();
    expect(":iframe .child-options-target").toHaveClass("class_apply_to");
    expect("[data-class-action='class_apply_to']").toHaveClass("active");
    expect(".options-container button.dropdown-toggle").toHaveText("Option 1");
});

test("The applyTo feature is changing the BuilderSearchSelect items visibility", async () => {
    addBuilderOption({
        selector: ".parent-options-target",
        template: xml`
            <BuilderRow label.translate="Test 0">
                <BuilderButton applyTo="'.child-options-target'" classAction="'class_apply_to'"/>
            </BuilderRow>
            <BuilderRow label.translate="Test 1">
                <BuilderSearchSelect choices="[
                        {
                            label: 'Option 0',
                            props: {
                                classAction: 'class_0',
                                applyTo: '.class_apply_to'
                            }
                        },
                        {
                            label: 'Option 1',
                            props: {
                                classAction: 'class_1',
                            }
                        },
                    ]"
                />
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(
        `<div class="parent-options-target class_1"><div class="child-options-target">Content...</div></div>`
    );

    await contains(":iframe .parent-options-target").click();
    expect("[data-class-action='class_apply_to']").not.toHaveClass("active");
    expect(".options-container button.dropdown-toggle").toHaveCount(1);
    await contains("[data-label='Test 1'] .dropdown-toggle").click();
    expect(queryAllTexts(".o-dropdown--menu span.o-dropdown-item")).toEqual(["Option 1"]);

    await contains("[data-class-action='class_apply_to']").click();
    expect(":iframe .child-options-target").toHaveClass("class_apply_to");
    expect("[data-class-action='class_apply_to']").toHaveClass("active");
    await contains("[data-label='Test 1'] .dropdown-toggle").click();
    expect(queryAllTexts(".o-dropdown--menu span.o-dropdown-item")).toEqual([
        "Option 0",
        "Option 1",
    ]);
});

test("Preview BuilderSearchSelect options (on hover)", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect attributeAction="'title'" choices="[
                        {
                            label: 'Option 0',
                            props: { attributeActionValue: 'Title 0' }
                        },
                        {
                            label: 'Option 1',
                            props: { attributeActionValue: 'Title 1' }
                        },
                    ]"
                />
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`);
    await contains(":iframe .test-options-target").click();
    expect(":iframe .test-options-target").not.toHaveAttribute("title");
    await contains("[data-label='Test'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu span.o-dropdown-item:contains('Option 1')").hover();
    expect(":iframe .test-options-target").toHaveAttribute("title", "Title 1");
    await contains(".we-bg-options-container").hover();
    expect(":iframe .test-options-target").not.toHaveAttribute("title");
    await contains(".o-dropdown--menu span.o-dropdown-item:contains('Option 0')").hover();
    expect(":iframe .test-options-target").toHaveAttribute("title", "Title 0");
    await click(".we-bg-options-container");
    expect(":iframe .test-options-target").not.toHaveAttribute("title");
});

test("Preview BuilderSearchSelect groups/options (keyboard navigation)", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect dataAttributeAction="'option'" groups="[
                        {
                            label: 'Group 0',
                            choices: [
                                {
                                    label: 'Group 0 > Option 0',
                                    props: { dataAttributeActionValue: '0' }
                                },
                                {
                                    label: 'Group 0 > Option 1',
                                    props: { dataAttributeActionValue: '1' }
                                },
                            ],
                        },
                        {
                            label: 'Group 1',
                            choices: [
                                {
                                    label: 'Group 1 > Option 0',
                                    props: { dataAttributeActionValue: '2' }
                                },
                            ],
                        },
                    ]"
                />
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`);
    await contains(":iframe .test-options-target").click();
    expect(":iframe .test-options-target").not.toHaveAttribute("data-option");
    await contains("[data-label='Test'] .dropdown-toggle").click();
    await press("arrowdown");
    expect(":iframe .test-options-target").toHaveAttribute("data-option", "0");
    await animationFrame();
    await press("arrowdown");
    await animationFrame();
    await press("arrowdown");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveAttribute("data-option", "2");
    await press("arrowdown");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveAttribute("data-option", "0");
});

// This test is using same logic and scenarios as in the `BuilderSelect`
// and `BuilderSelectItem` components (see `builder_select_item.test.js`).
describe("LTR - RTL compatibility", () => {
    before(() => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label.translate="Test">
                    <BuilderSearchSelect choices="[
                            {
                                label: 'Left',
                                props: {
                                    classAction: 'class_0',
                                    ltrRtlMapping: 'left-right',
                                },
                                attrs: { title: 'Left' },
                            },
                            {
                                label: 'Right',
                                props: {
                                    classAction: 'class_1',
                                    ltrRtlMapping: 'left-right',
                                },
                                attrs: { title: 'Right' },
                            },
                        ]"/>
                </BuilderRow>
            `,
        });
    });

    test("Iframe and Builder LTR", async () => {
        await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`);
        await contains(":iframe .test-options-target").click();
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        expect(".popover [data-choice-index='0']").toHaveAttribute("title", "Left");
        expect(".popover [data-choice-index='1']").toHaveAttribute("title", "Right");

        await contains(".popover [data-choice-index='0']").click();
        expect(":iframe .test-options-target").toHaveClass("class_0");
        expect(":iframe .test-options-target").not.toHaveClass("class_1");
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        await contains(".popover [data-choice-index='1']").click();
        expect(":iframe .test-options-target").toHaveClass("class_1");
        expect(":iframe .test-options-target").not.toHaveClass("class_0");
    });

    test("Iframe and Builder RTL", async () => {
        onRpc("/web/webclient/translations", () => ({
            hash: "aaa",
            lang: "ar-001",
            lang_parameters: {
                direction: "rtl",
                grouping: "[3,0]",
                date_format: "%m/%d/%Y",
                time_format: "%H:%M:%S",
            },
            modules: {},
        }));
        getFixture().style.setProperty("direction", "rtl");

        await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`, {
            iframeLangDir: "rtl",
        });
        await contains(":iframe .test-options-target").click();
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        expect(".popover [data-choice-index='0']").toHaveAttribute("title", "Right");
        expect(".popover [data-choice-index='1']").toHaveAttribute("title", "Left");

        await contains(".popover [data-choice-index='0']").click();
        expect(":iframe .test-options-target").toHaveClass("class_0");
        expect(":iframe .test-options-target").not.toHaveClass("class_1");
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        await contains(".popover [data-choice-index='1']").click();
        expect(":iframe .test-options-target").toHaveClass("class_1");
        expect(":iframe .test-options-target").not.toHaveClass("class_0");
    });

    test("Iframe LTR and Builder RTL", async () => {
        onRpc("/web/webclient/translations", () => ({
            hash: "aaa",
            lang: "ar-001",
            lang_parameters: {
                direction: "rtl",
                grouping: "[3,0]",
                date_format: "%m/%d/%Y",
                time_format: "%H:%M:%S",
            },
            modules: {},
        }));
        getFixture().style.setProperty("direction", "rtl");

        await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`);
        await contains(":iframe .test-options-target").click();
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        expect(".popover [data-choice-index='0']").toHaveAttribute("title", "Right");
        expect(".popover [data-choice-index='1']").toHaveAttribute("title", "Left");

        await contains(".popover [data-choice-index='0']").click();
        expect(":iframe .test-options-target").toHaveClass("class_1");
        expect(":iframe .test-options-target").not.toHaveClass("class_0");
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        await contains(".popover [data-choice-index='1']").click();
        expect(":iframe .test-options-target").toHaveClass("class_0");
        expect(":iframe .test-options-target").not.toHaveClass("class_1");
    });

    test("Iframe RTL and Builder LTR", async () => {
        await setupHTMLBuilder(`<div class="test-options-target">Content...</div>`, {
            iframeLangDir: "rtl",
        });
        await contains(":iframe .test-options-target").click();
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        expect(".popover [data-choice-index='0']").toHaveAttribute("title", "Left");
        expect(".popover [data-choice-index='1']").toHaveAttribute("title", "Right");

        await contains(".popover [data-choice-index='0']").click();
        expect(":iframe .test-options-target").toHaveClass("class_1");
        expect(":iframe .test-options-target").not.toHaveClass("class_0");
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        await contains(".popover [data-choice-index='1']").click();
        expect(":iframe .test-options-target").toHaveClass("class_0");
        expect(":iframe .test-options-target").not.toHaveClass("class_1");
    });
});
