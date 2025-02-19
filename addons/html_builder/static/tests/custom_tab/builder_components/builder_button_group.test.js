import { expect, test } from "@odoo/hoot";
import { hover } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "../../website_helpers";

defineWebsiteModels();

test("change the editingElement of sub widget through `applyTo` prop", async () => {
    addActionOption({
        customAction: {
            apply: ({ editingElement }) => {
                expect.step(`customAction ${editingElement.className}`);
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
                    <BuilderButtonGroup applyTo="'.a'">
                        <BuilderButton action="'customAction'"/>
                    </BuilderButtonGroup>`,
    });
    await setupWebsiteBuilder(`
                <div class="test-options-target">
                    <div class="a">b</div>
                </div>
            `);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await hover("[data-action-id='customAction']");
    expect.verifySteps(["customAction a"]);
});
test("should propagate actionParam in the context", async () => {
    addActionOption({
        customAction: {
            apply: ({ param: { mainParam: testParam } }) => {
                expect.step(`customAction ${testParam}`);
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
                    <BuilderButtonGroup actionParam="'myParam'">
                        <BuilderButton action="'customAction'"/>
                    </BuilderButtonGroup>`,
    });
    await setupWebsiteBuilder(`
                <div class="test-options-target">
                    <div class="a">b</div>
                </div>
            `);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await hover("[data-action-id='customAction']");
    expect.verifySteps(["customAction myParam"]);
});
test("prevent preview of all buttons", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`
                    <BuilderButtonGroup preview="false">
                        <BuilderButton action="'customAction1'"/>
                        <BuilderButton action="'customAction2'" preview="true"/>
                    </BuilderButtonGroup>
                    <BuilderButtonGroup preview="true">
                        <BuilderButton action="'customAction3'"/>
                    </BuilderButtonGroup>
                    <BuilderButtonGroup>
                        <BuilderButton action="'customAction4'"/>
                    </BuilderButtonGroup>`,
    });
    addActionOption({
        customAction1: {
            apply: () => expect.step(`customAction1`),
        },
        customAction2: {
            apply: () => expect.step(`customAction2`),
        },
        customAction3: {
            apply: () => expect.step(`customAction3`),
        },
        customAction4: {
            apply: () => expect.step(`customAction4`),
        },
    });
    await setupWebsiteBuilder(`
                <div class="test-options-target">
                    <div class="a">b</div>
                </div>
            `);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains("[data-action-id='customAction1']").hover();
    expect.verifySteps([]);
    await contains("[data-action-id='customAction2']").hover();
    expect.verifySteps(["customAction2"]);
    await contains("[data-action-id='customAction3']").hover();
    expect.verifySteps(["customAction3"]);
    await contains("[data-action-id='customAction4']").hover();
    expect.verifySteps(["customAction4"]);
});
test("hide/display base on applyTo", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });

    addOption({
        selector: ".parent-target",
        template: xml`
                <BuilderButtonGroup applyTo="'.my-custom-class'">
                    <BuilderButton classAction="'test'">Test</BuilderButton>
                </BuilderButtonGroup>`,
    });

    await setupWebsiteBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target").click();
    expect(".options-container .btn-group").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container .btn-group").toHaveCount(1);
});

test("hide/display base on applyTo - 2", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });

    addOption({
        selector: ".parent-target",
        template: xml`
                <BuilderButtonGroup>
                    <BuilderButton applyTo="'.my-custom-class'" classAction="'test'">Test</BuilderButton>
                </BuilderButtonGroup>`,
    });

    await setupWebsiteBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target").click();
    expect(".options-container .btn-group").not.toBeVisible();

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container .btn-group").toBeVisible();
});

test("click on BuilderButton with empty value should remove styleAction", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButtonGroup>
            <BuilderButton styleAction="'width'" styleActionValue="''"/>
            <BuilderButton styleAction="'width'" styleActionValue="'25%'"/>
        </BuilderButtonGroup>`,
    });
    const { getEditableContent } = await setupWebsiteBuilder(
        `<div class="test-options-target">b</div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .test-options-target").click();
    await contains("[data-style-action='width'][data-style-action-value='25%']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target" style="width: 25% !important;">b</div>`
    );

    await contains("[data-style-action='width'][data-style-action-value='']").click();
    expect(editableContent).toHaveInnerHTML(`<div class="test-options-target" style="">b</div>`);
});
