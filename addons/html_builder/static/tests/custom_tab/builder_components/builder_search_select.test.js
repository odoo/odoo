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
                <BuilderSearchSelect choices="[{ label: 'Option 0' }]"
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
    expect.verifySteps(["customAction: param_0 > value_0", "customAction: param_0 > value_0"]);
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
    expect.verifySteps(["size: 50/75", "color: Green", "color: Green"]);
    expect(":iframe .test-options-target").toHaveStyle({ opacity: "0.75" });
});

test("Call a combination of BuilderSearchSelect and BuilderSearchSelect item actions (using groups)", async () => {
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
                                    label: 'Option 0.0',
                                    props: {
                                        action: 'sizeAction',
                                        actionParam: { H: 75, W: 100 },
                                        classAction: '',
                                        styleActionValue: '0',
                                    }
                                },
                                {
                                    label: 'Option 0.1',
                                    props: {
                                        action: 'sizeAction',
                                        actionParam: { H: 25, W: 25 },
                                        classAction: 'class_01',
                                        styleActionValue: '0.5',
                                    }
                                }
                            ],
                        },
                        {
                            label: 'Group 1',
                            choices: [
                                {
                                    label: 'Option 1.0',
                                    props: {
                                        action: 'colorAction',
                                        actionParam: { H: 50, W: 100 },
                                        classAction: 'class_10',
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
});

test("Use isActiveItem for an options in the BuilderSearchSelect", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSearchSelect choices="[
                        {
                            label: 'item_label_0',
                            props: {
                                classAction: 'item_0_class',
                            }
                        },
                        {
                            id: 'item_1_opt',
                            label: 'item_label_1',
                            props: {
                                classAction: 'item_1_class',
                            }
                        },
                    ]"
                />
                <div class="dependency" t-if="this.isActiveItem('item_1_opt')">Dependency...</div>
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target item_0_class">Content...</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(1);
    expect("[data-label='Test'] .dropdown-toggle").toHaveText("item_label_0");
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
                                classAction: 'bg-warning',
                            }
                        },
                        {
                            label: 'Style 2',
                            props: {
                                classAction: 'item_2_class bg-success',
                            }
                        },
                    ]"
                />
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target bg-warning">Content...</div>`);
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
