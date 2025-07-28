import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { describe, expect, test } from "@odoo/hoot";
import { hover } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";

describe.current.tags("desktop");

test("change the editingElement of sub widget through `applyTo` prop", async () => {
    class CustomAction extends BuilderAction {
        static id = "customAction";
        apply({ editingElement }) {
            expect.step(`customAction ${editingElement.className}`);
        }
    }
    addBuilderAction({
        CustomAction,
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                    <BuilderButtonGroup applyTo="'.a'">
                        <BuilderButton action="'customAction'"/>
                    </BuilderButtonGroup>`;
        }
    );
    await setupHTMLBuilder(`
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
    class CustomAction extends BuilderAction {
        static id = "customAction";
        apply({ params: { mainParam: testParam } }) {
            expect.step(`customAction ${testParam}`);
        }
    }
    addBuilderAction({
        CustomAction,
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                    <BuilderButtonGroup actionParam="'myParam'">
                        <BuilderButton action="'customAction'"/>
                    </BuilderButtonGroup>`;
        }
    );
    await setupHTMLBuilder(`
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
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                    <BuilderButtonGroup preview="false">
                        <BuilderButton action="'customAction1'"/>
                        <BuilderButton action="'customAction2'" preview="true"/>
                    </BuilderButtonGroup>
                    <BuilderButtonGroup preview="true">
                        <BuilderButton action="'customAction3'"/>
                    </BuilderButtonGroup>
                    <BuilderButtonGroup>
                        <BuilderButton action="'customAction4'"/>
                    </BuilderButtonGroup>`;
        }
    );
    class CustomAction1 extends BuilderAction {
        static id = "customAction1";
        apply() {
            return expect.step(`customAction1`);
        }
    }
    class CustomAction2 extends BuilderAction {
        static id = "customAction2";
        apply() {
            return expect.step(`customAction2`);
        }
    }
    class CustomAction3 extends BuilderAction {
        static id = "customAction3";
        apply() {
            return expect.step(`customAction3`);
        }
    }
    class CustomAction4 extends BuilderAction {
        static id = "customAction4";
        apply() {
            return expect.step(`customAction4`);
        }
    }
    addBuilderAction({
        CustomAction1,
        CustomAction2,
        CustomAction3,
        CustomAction4,
    });
    await setupHTMLBuilder(`
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
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`;
        }
    );

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`
                <BuilderButtonGroup applyTo="'.my-custom-class'">
                    <BuilderButton classAction="'test'">Test</BuilderButton>
                </BuilderButtonGroup>`;
        }
    );

    await setupHTMLBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target").click();
    expect(".options-container .btn-group").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container .btn-group").toHaveCount(1);
});

test("hide/display base on applyTo - 2", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`;
        }
    );

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`
                <BuilderButtonGroup>
                    <BuilderButton applyTo="'.my-custom-class'" classAction="'test'">Test</BuilderButton>
                </BuilderButtonGroup>`;
        }
    );

    await setupHTMLBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target").click();
    expect(".options-container .btn-group").not.toBeVisible();

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container .btn-group").toBeVisible();
});

test("click on BuilderButton with empty value should remove styleAction", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButtonGroup>
            <BuilderButton styleAction="'width'" styleActionValue="''"/>
            <BuilderButton styleAction="'width'" styleActionValue="'25%'"/>
        </BuilderButtonGroup>`;
        }
    );
    const { contentEl } = await setupHTMLBuilder(`<p class="test-options-target">b</p>`);
    await contains(":iframe .test-options-target").click();
    await contains("[data-style-action='width'][data-style-action-value='25%']").click();
    expect(contentEl).toHaveInnerHTML(
        `<p class="test-options-target" style="width: 25% !important;">b</p>`
    );

    await contains("[data-style-action='width'][data-style-action-value='']").click();
    expect(contentEl).toHaveInnerHTML(`<p class="test-options-target" style="">b</p>`);
});

test("button that matches with the highest priority should be active", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButtonGroup>
                <BuilderButton classAction="'a'" >a</BuilderButton>
                <BuilderButton classAction="'a b'">a b</BuilderButton>
                <BuilderButton classAction="'a b c'">a b c</BuilderButton>
        </BuilderButtonGroup>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target a b">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect("[data-class-action='a']").not.toHaveClass("active");
    expect("[data-class-action='a b']").toHaveClass("active");
    expect("[data-class-action='a b c']").not.toHaveClass("active");
});
