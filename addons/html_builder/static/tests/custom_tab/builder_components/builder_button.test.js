import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, hover, runAllTimers } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "../../helpers";

defineWebsiteModels();

test("call a specific action with some params and value", async () => {
    addActionOption({
        customAction: {
            apply: ({ param, value }) => {
                expect.step(`customAction ${param} ${value}`);
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'" actionParam="'myParam'" actionValue="'myValue'">MyAction</BuilderButton>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect("[data-action-id='customAction']").toHaveText("MyAction");
    await click("[data-action-id='customAction']");
    // The function `apply` should be called twice (on hover (for preview), then, on click).
    expect.verifySteps(["customAction myParam myValue", "customAction myParam myValue"]);
});
test("call a shorthand action", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton classAction="'my-custom-class'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await click("[data-class-action='my-custom-class']");
    expect(":iframe .test-options-target").toHaveClass("my-custom-class");
});
test("call a shorthand action and a specific action", async () => {
    addActionOption({
        customAction: {
            apply: ({ editingElement }) => {
                expect.step(`customAction`);
                editingElement.innerHTML = "c";
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'" classAction="'my-custom-class'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await click("[data-action-id='customAction'][data-class-action='my-custom-class']");
    expect(":iframe .test-options-target").toHaveClass("my-custom-class");
    // The function `apply` should be called twice (on hover (for preview), then, on click).
    expect.verifySteps(["customAction", "customAction"]);
    expect(":iframe .test-options-target").toHaveInnerHTML("c");
});
test("preview a shorthand action and a specific action", async () => {
    addActionOption({
        customAction: {
            apply: ({ editingElement }) => {
                expect.step(`customAction`);
                editingElement.innerHTML = "c";
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'" classAction="'my-custom-class'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await hover("[data-action-id='customAction'][data-class-action='my-custom-class']");
    expect(":iframe .test-options-target").toHaveClass("my-custom-class");
    expect.verifySteps(["customAction"]);
    expect(":iframe .test-options-target").toHaveInnerHTML("c");
    await hover(".test-options-target");
    expect(":iframe .test-options-target").toHaveInnerHTML("b");
    expect.verifySteps([]);
});
test("prevent preview of a specific action", async () => {
    addActionOption({
        customAction: {
            apply: () => {
                expect.step(`customAction`);
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'" preview="false"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    const c = contains("[data-action-id='customAction']");
    await c.hover();
    expect.verifySteps([]);
    await c.click();
    expect.verifySteps(["customAction"]);
});
test("clean another action", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`
                    <BuilderButtonGroup>
                        <BuilderButton classAction="'my-custom-class1'"/>
                        <BuilderButton classAction="'my-custom-class2'"/>
                    </BuilderButtonGroup>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await click("[data-class-action='my-custom-class1']");
    expect(":iframe .test-options-target").toHaveAttribute(
        "class",
        "test-options-target my-custom-class1"
    );
    await click("[data-class-action='my-custom-class2']");
    expect(":iframe .test-options-target").toHaveAttribute(
        "class",
        "test-options-target my-custom-class2"
    );
});
test("add the active class if the condition is met", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`
                        <BuilderButton classAction="'my-custom-class1'"/>
                        <BuilderButton classAction="'my-custom-class2'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target my-custom-class1">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect("[data-class-action='my-custom-class1']").toHaveClass("active");
    expect("[data-class-action='my-custom-class2']").not.toHaveClass("active");
});
test("apply classAction on multi elements", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton applyTo="'.target-apply'" classAction="'my-custom-class'"/>`,
    });
    const { getEditor } = await setupWebsiteBuilder(`
            <div class="test-options-target">
                <div class="target-apply">a</div>
                <div class="target-apply">b</div>
            </div>`);
    const editor = getEditor();
    await contains(":iframe .test-options-target").click();
    expect(editor.editable).toHaveInnerHTML(`
            <div class="test-options-target">
                <div class="target-apply">a</div>
                <div class="target-apply">b</div>
            </div>`);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editor.editable).toHaveInnerHTML(`
            <div class="test-options-target">
                <div class="target-apply my-custom-class">a</div>
                <div class="target-apply my-custom-class">b</div>
            </div>`);
});
test("hide/display base on applyTo", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderRow label="'my label'">
                <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderRow label="'my label'">
                <BuilderButton applyTo="'.my-custom-class'" classAction="'test'"/>
            </BuilderRow>`,
    });

    const { getEditor } = await setupWebsiteBuilder(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    const editor = getEditor();
    await contains(":iframe .parent-target").click();
    expect(editor.editable).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect("[data-class-action='test']").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editor.editable).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect("[data-class-action='test']").toHaveCount(1);
    expect("[data-class-action='test']").not.toHaveClass("active");
});
describe("inherited actions", () => {
    function makeAction(n, { async } = {}) {
        const action = {
            clean({ param, value }) {
                expect.step(`customAction${n} clean ${param} ${value}`);
            },
            apply: ({ param, value }) => {
                expect.step(`customAction${n} apply ${param} ${value}`);
            },
        };
        if (async) {
            let resolve;
            const promise = new Promise((r) => {
                resolve = r;
            });
            action.load = async ({ param, value }) => {
                expect.step(`customAction${n} load ${param} ${value}`);
                return promise;
            };
            return { action, resolve };
        }
        return { action };
    }
    test("inherit actions for another button", async () => {
        addActionOption({
            customAction1: makeAction(1).action,
            customAction2: makeAction(2).action,
            customAction3: makeAction(3).action,
        });
        addOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderButtonGroup>
                    <BuilderButton action="'customAction1'" actionParam="'myParam1'" actionValue="'myValue1'"  id="'c1'">MyAction1</BuilderButton>
                    <BuilderButton action="'customAction2'" actionParam="'myParam2'" actionValue="'myValue2'">MyAction2</BuilderButton>
                </BuilderButtonGroup>
                <BuilderButton action="'customAction3'" actionParam="'myParam3'" actionValue="'myValue3'" inheritedActions="['c1']" >MyAction2</BuilderButton>
            `,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">a</div>`);
        await contains(":iframe .test-options-target").click();

        await contains("[data-action-id='customAction3']").hover();
        expect.verifySteps([
            "customAction2 clean myParam2 myValue2",
            "customAction1 clean myParam1 myValue1",

            "customAction3 apply myParam3 myValue3",
            "customAction1 apply myParam1 myValue1",
        ]);
    });
    test("inherit actions for another button (with async)", async () => {
        const action1 = makeAction(1, { async: true });
        const action2 = makeAction(2, { async: true });
        const action3 = makeAction(3, { async: true });
        const action4 = makeAction(4, { async: true });
        addActionOption({
            customAction1: action1.action,
            customAction2: action2.action,
            customAction3: action3.action,
            customAction4: action4.action,
        });
        addOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderButtonGroup>
                    <BuilderButton action="'customAction1'" actionParam="'myParam1'" actionValue="'myValue1'"  id="'c1'">MyAction1</BuilderButton>
                    <BuilderButton action="'customAction2'" actionParam="'myParam2'" actionValue="'myValue2'">MyAction2</BuilderButton>
                </BuilderButtonGroup>
                <BuilderButton action="'customAction3'" actionParam="'myParam3'" actionValue="'myValue3'"  id="'c3'">MyAction1</BuilderButton>
                <BuilderButton action="'customAction4'" actionParam="'myParam4'" actionValue="'myValue4'" inheritedActions="['c1', 'c3']" >MyAction2</BuilderButton>
            `,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">a</div>`);
        await contains(":iframe .test-options-target").click();

        await contains("[data-action-id='customAction4']").hover();
        action4.resolve();
        action3.resolve();
        action1.resolve();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect.verifySteps([
            "customAction4 load myParam4 myValue4",
            "customAction1 load myParam1 myValue1",
            "customAction3 load myParam3 myValue3",

            "customAction2 clean myParam2 myValue2",
            "customAction1 clean myParam1 myValue1",

            "customAction4 apply myParam4 myValue4",
            "customAction1 apply myParam1 myValue1",
            "customAction3 apply myParam3 myValue3",
        ]);
    });
});
describe("Operation", () => {
    function makeAsyncActionItem(actionName) {
        const item = {};
        const promise = new Promise((resolve) => {
            item.resolve = resolve;
        });
        addActionOption({
            [actionName]: {
                load: async () => {
                    expect.step(`load ${actionName}`);
                    await promise;
                },
                apply: async ({ editingElement }) => {
                    expect.step(`apply ${actionName}`);
                    editingElement.innerText = editingElement.innerText + `-${actionName}`;
                },
            },
        });
        return item;
    }
    function makeActionItem(actionName) {
        addActionOption({
            [actionName]: {
                apply: ({ editingElement }) => {
                    expect.step(actionName);
                    editingElement.innerText = editingElement.innerText + `-${actionName}`;
                },
            },
        });
    }

    test("handle async actions with commit and preview (separated by running all timers)", async () => {
        const asyncAction1 = makeAsyncActionItem("asyncAction1");
        const asyncAction2 = makeAsyncActionItem("asyncAction2");
        const asyncAction3 = makeAsyncActionItem("asyncAction3");
        makeActionItem("action1");
        makeActionItem("action2");

        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderRow label="'my label'">
                <BuilderButton action="'asyncAction1'"/>
                <BuilderButton action="'asyncAction2'"/>
                <BuilderButton action="'asyncAction3'"/>
                <BuilderButton action="'action1'"/>
                <BuilderButton action="'action2'"/>
            </BuilderRow>`,
        });

        await setupWebsiteBuilder(`<div class="test-options-target">a</div>`);
        await contains(":iframe .test-options-target").click();

        await hover("[data-action-id='asyncAction1']");
        await animationFrame();
        await hover("[data-action-id='asyncAction2']");
        await animationFrame();
        await hover("[data-action-id='asyncAction3']");
        await animationFrame();
        await contains("[data-action-id='asyncAction3']").click();
        await hover("[data-action-id='action1']");
        await animationFrame();

        asyncAction1.resolve();
        asyncAction2.resolve();
        asyncAction3.resolve();
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect.verifySteps([
            "load asyncAction1",
            "load asyncAction3",
            "apply asyncAction3",
            "action1",
        ]);
        expect(":iframe .test-options-target").toHaveInnerHTML("a-asyncAction3-action1");

        // If the code is not working properly, hovering on another action at
        // this moment could revert the changes made by asyncAction3 through the
        // revert of the preview. In order to test this case, we hover action2.
        await hover("[data-action-id='action2']");
        await animationFrame();
        expect(":iframe .test-options-target").toHaveInnerHTML("a-asyncAction3-action2");
        expect.verifySteps(["action2"]);
    });
    test("handle async actions with commit and preview (separated by animation frame)", async () => {
        const asyncAction1 = makeAsyncActionItem("asyncAction1");
        const asyncAction2 = makeAsyncActionItem("asyncAction2");
        const asyncAction3 = makeAsyncActionItem("asyncAction3");
        makeActionItem("action1");
        makeActionItem("action2");

        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderRow label="'my label'">
                <BuilderButton action="'asyncAction1'"/>
                <BuilderButton action="'asyncAction2'"/>
                <BuilderButton action="'asyncAction3'"/>
                <BuilderButton action="'action1'"/>
                <BuilderButton action="'action2'"/>
            </BuilderRow>`,
        });

        await setupWebsiteBuilder(`<div class="test-options-target">a</div>`);
        await contains(":iframe .test-options-target").click();

        await hover("[data-action-id='asyncAction1']");
        await runAllTimers();
        await hover("[data-action-id='asyncAction2']");
        await runAllTimers();
        await hover("[data-action-id='asyncAction3']");
        await runAllTimers();
        await contains("[data-action-id='asyncAction3']").click();
        await hover("[data-action-id='action1']");
        await runAllTimers();

        asyncAction1.resolve();
        asyncAction2.resolve();
        asyncAction3.resolve();
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect.verifySteps([
            "load asyncAction1",
            "load asyncAction2",
            "load asyncAction3",
            "load asyncAction3",
            "apply asyncAction3",
            "action1",
        ]);
        expect(":iframe .test-options-target").toHaveInnerHTML("a-asyncAction3-action1");

        // If the code is not working properly, hovering on another action at
        // this moment could revert the changes made by asyncAction3 through the
        // revert of the preview. In order to test this case, we hover action2.
        await hover("[data-action-id='action2']");
        await animationFrame();
        expect(":iframe .test-options-target").toHaveInnerHTML("a-asyncAction3-action2");
        expect.verifySteps(["action2"]);
    });
});
