import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    fill,
    hover,
    queryAllTexts,
    queryFirst,
    runAllTimers,
    waitFor,
} from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addActionOption, addOption, defineWebsiteModels, setupWebsiteBuilder } from "../helpers";

defineWebsiteModels();

describe("WeRow", () => {
    test("show row title", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<WeRow label="'my label'">row text</WeRow>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".hb-row .text-nowrap").toHaveText("my label");
    });
    test("show row tooltip", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<WeRow label="'my label'" tooltip="'my tooltip'">row text</WeRow>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".hb-row .text-nowrap").toHaveText("my label");
        expect(".o-tooltip").not.toBeDisplayed();
        await hover(".hb-row .text-nowrap");
        await waitFor(".o-tooltip", { timeout: 1000 });
        expect(".o-tooltip").toHaveText("my tooltip");
        await contains(":iframe .test-options-target").hover();
        expect(".o-tooltip").not.toBeDisplayed();
    });
    test("hide empty row and display row with content", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeRow label="'Row 1'">
                <WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </WeRow>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`<WeRow label="'Row 2'">
                <WeButton applyTo="':not(.my-custom-class)'" classAction="'test'"/>
            </WeRow>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`<WeRow label="'Row 3'">
                <WeButton applyTo="'.my-custom-class'" classAction="'test'"/>
            </WeRow>`,
        });
        await setupWebsiteBuilder(
            `<div class="parent-target"><div class="child-target">b</div></div>`
        );
        const selectorRowLabel = ".options-container .hb-row:not(.d-none) > div:nth-child(1)";
        await contains(":iframe .parent-target").click();
        expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 2"]);

        await contains("[data-class-action='my-custom-class']").click();
        expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 3"]);
    });
    test("extra classes on WeRow", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<WeRow label="'my label'" extraClassName="'extra-class'">row text</WeRow>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".hb-row").toHaveClass("extra-class");
    });
});
describe("WeButton", () => {
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
            template: xml`<WeButton action="'customAction'" actionParam="'myParam'" actionValue="'myValue'">MyAction</WeButton>`,
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
            template: xml`<WeButton classAction="'my-custom-class'"/>`,
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
            template: xml`<WeButton action="'customAction'" classAction="'my-custom-class'"/>`,
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
            template: xml`<WeButton action="'customAction'" classAction="'my-custom-class'"/>`,
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
            template: xml`<WeButton action="'customAction'" preview="false"/>`,
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
                    <WeButtonGroup>
                        <WeButton classAction="'my-custom-class1'"/>
                        <WeButton classAction="'my-custom-class2'"/>
                    </WeButtonGroup>`,
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
                        <WeButton classAction="'my-custom-class1'"/>
                        <WeButton classAction="'my-custom-class2'"/>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target my-custom-class1">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect("[data-class-action='my-custom-class1']").toHaveClass("active");
        expect("[data-class-action='my-custom-class2']").not.toHaveClass("active");
    });
    test("apply classAction on multi elements", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<WeButton applyTo="'.target-apply'" classAction="'my-custom-class'"/>`,
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
            template: xml`<WeRow label="'my label'">
                <WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </WeRow>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`<WeRow label="'my label'">
                <WeButton applyTo="'.my-custom-class'" classAction="'test'"/>
            </WeRow>`,
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
    test("inherit actions for another button", async () => {
        function makeAction(n) {
            return {
                clean({ param, value }) {
                    expect.step(`customAction${n} clean ${param} ${value}`);
                },
                apply: ({ param, value }) => {
                    expect.step(`customAction${n} apply ${param} ${value}`);
                },
            };
        }
        addActionOption({
            customAction1: makeAction(1),
            customAction2: makeAction(2),
            customAction3: makeAction(3),
        });
        addOption({
            selector: ".test-options-target",
            template: xml`
                <WeButtonGroup>
                    <WeButton action="'customAction1'" actionParam="'myParam1'" actionValue="'myValue1'"  id="'c1'">MyAction1</WeButton>
                    <WeButton action="'customAction2'" actionParam="'myParam2'" actionValue="'myValue2'">MyAction2</WeButton>
                </WeButtonGroup>
                <WeButton action="'customAction3'" actionParam="'myParam3'" actionValue="'myValue3'" inheritedActions="'c1'" >MyAction2</WeButton>
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
                template: xml`<WeRow label="'my label'">
                <WeButton action="'asyncAction1'"/>
                <WeButton action="'asyncAction2'"/>
                <WeButton action="'asyncAction3'"/>
                <WeButton action="'action1'"/>
                <WeButton action="'action2'"/>
            </WeRow>`,
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
                template: xml`<WeRow label="'my label'">
                <WeButton action="'asyncAction1'"/>
                <WeButton action="'asyncAction2'"/>
                <WeButton action="'asyncAction3'"/>
                <WeButton action="'action1'"/>
                <WeButton action="'action2'"/>
            </WeRow>`,
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
});
describe("WeButtonGroup", () => {
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
                    <WeButtonGroup applyTo="'.a'">
                        <WeButton action="'customAction'"/>
                    </WeButtonGroup>`,
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
                apply: ({ param }) => {
                    expect.step(`customAction ${param}`);
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`
                    <WeButtonGroup actionParam="'myParam'">
                        <WeButton action="'customAction'"/>
                    </WeButtonGroup>`,
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
                    <WeButtonGroup preview="false">
                        <WeButton action="'customAction1'"/>
                        <WeButton action="'customAction2'" preview="true"/>
                    </WeButtonGroup>
                    <WeButtonGroup preview="true">
                        <WeButton action="'customAction3'"/>
                    </WeButtonGroup>
                    <WeButtonGroup>
                        <WeButton action="'customAction4'"/>
                    </WeButtonGroup>`,
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
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });

        addOption({
            selector: ".parent-target",
            template: xml`
                <WeButtonGroup applyTo="'.my-custom-class'">
                    <WeButton classAction="'test'">Test</WeButton>
                </WeButtonGroup>`,
        });

        await setupWebsiteBuilder(
            `<div class="parent-target"><div class="child-target">b</div></div>`
        );
        await contains(":iframe .parent-target").click();
        expect(".options-container .btn-group").toHaveCount(0);

        await contains("[data-class-action='my-custom-class']").click();
        expect(".options-container .btn-group").toHaveCount(1);
    });

    test("hide/display base on applyTo - 2", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });

        addOption({
            selector: ".parent-target",
            template: xml`
                <WeButtonGroup>
                    <WeButton applyTo="'.my-custom-class'" classAction="'test'">Test</WeButton>
                </WeButtonGroup>`,
        });

        await setupWebsiteBuilder(
            `<div class="parent-target"><div class="child-target">b</div></div>`
        );
        await contains(":iframe .parent-target").click();
        expect(".options-container .btn-group").not.toBeVisible();

        await contains("[data-class-action='my-custom-class']").click();
        expect(".options-container .btn-group").toBeVisible();
    });
});
describe("WeNumberInput", () => {
    test("should get the initial value of the input", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ param }) => {
                    expect.step(`customAction ${param}`);
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<WeNumberInput action="'customAction'"/>`,
        });
        await setupWebsiteBuilder(`
                <div class="test-options-target">10</div>
            `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("10");
    });
    test("should preview changes", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ editingElement, value }) => {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<WeNumberInput action="'customAction'"/>`,
        });
        await setupWebsiteBuilder(`
                <div class="test-options-target">10</div>
            `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        await fill("2");
        expect.verifySteps(["customAction 102"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
        expect(".o-snippets-top-actions .fa-undo").not.toBeEnabled();
        expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
    });
    test("should commit changes", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ editingElement, value }) => {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<WeNumberInput action="'customAction'"/>`,
        });
        await setupWebsiteBuilder(`
                <div class="test-options-target">10</div>
            `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        await fill("2");
        expect.verifySteps(["customAction 102"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
        await click(document.body);
        await animationFrame();
        expect.verifySteps(["customAction 102"]);
        expect(".o-snippets-top-actions .fa-undo").toBeEnabled();
        expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
    });
    test("hide/display base on applyTo", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`<WeNumberInput applyTo="'.my-custom-class'" action="'customAction'"/>`,
        });
        addActionOption({
            customAction: {
                getValue: () => "customValue",
            },
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
        expect("[data-action-id='customAction']").toHaveCount(0);

        await contains("[data-class-action='my-custom-class']").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target my-custom-class">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").toHaveClass("active");
        expect("[data-action-id='customAction']").toHaveCount(1);
        expect("[data-action-id='customAction'] input").toHaveValue("customValue");
    });
});
describe("WeTextInput", () => {
    test("hide/display base on applyTo", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`<WeTextInput applyTo="'.my-custom-class'" action="'customAction'"/>`,
        });
        addActionOption({
            customAction: {
                getValue: () => "customValue",
            },
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
        expect("[data-action-id='customAction']").toHaveCount(0);

        await contains("[data-class-action='my-custom-class']").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target my-custom-class">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").toHaveClass("active");
        expect("[data-action-id='customAction']").toHaveCount(1);
        expect("[data-action-id='customAction'] input").toHaveValue("customValue");
    });
});
describe("WeSelectItem", () => {
    test("call a specific action with some params and value (WeSelectItem)", async () => {
        addActionOption({
            customAction: {
                apply: ({ param, value }) => {
                    expect.step(`customAction ${param} ${value}`);
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`
                    <WeSelect>
                        <WeSelectItem action="'customAction'" actionParam="'myParam'" actionValue="'myValue'">MyAction</WeSelectItem>
                    </WeSelect>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        expect("[data-action-id='customAction']").toHaveText("MyAction");
        await click("[data-action-id='customAction']");
        // The function `apply` should be called twice (on hover (for preview), then, on click).
        expect.verifySteps(["customAction myParam myValue", "customAction myParam myValue"]);
    });
    test("set the label of the select from the active select item and be updated on undo/redo", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`
                    <WeSelect attributeAction="'customAttribute'">
                        <WeSelectItem attributeActionValue="null">None</WeSelectItem>
                        <WeSelectItem attributeActionValue="'a'">A</WeSelectItem>
                        <WeSelectItem attributeActionValue="'b'">B</WeSelectItem>
                    </WeSelect>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target" customAttribute="a">x</div>`);
        setSelection({
            anchorNode: queryFirst(":iframe .test-options-target").childNodes[0],
            anchorOffset: 0,
        });
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".we-bg-options-container .dropdown").toHaveText("A");
        await contains(".we-bg-options-container .dropdown").click();
        await contains(".o-overlay-item [data-attribute-action-value-id='b']").click();
        expect(".we-bg-options-container .dropdown").toHaveText("B");
        await animationFrame();
        expect(".o-overlay-item [data-attribute-action-value-id='b']").not.toBeDisplayed();
        await contains(".o-snippets-top-actions .fa-undo").click();
        expect(".we-bg-options-container .dropdown").toHaveText("A");
        await contains(".o-snippets-top-actions .fa-repeat").click();
        expect(".we-bg-options-container .dropdown").toHaveText("B");
    });
    test("consider the priority of the select item", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`
                    <WeSelect>
                        <WeSelectItem classAction="''">None</WeSelectItem>
                        <WeSelectItem classAction="'a'">A</WeSelectItem>
                        <WeSelectItem classAction="'a b'">A B</WeSelectItem>
                    </WeSelect>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target a">x</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();

        expect(".we-bg-options-container .dropdown").toHaveText("A");
        await contains(".we-bg-options-container .dropdown").click();

        await contains(".o-overlay-item [data-class-action='']").click();
        expect(".we-bg-options-container .dropdown").toHaveText("None");
        await contains(".we-bg-options-container .dropdown").click();

        await contains(".o-overlay-item [data-class-action='a b']").click();
        expect(".we-bg-options-container .dropdown").toHaveText("A B");
    });
    test("hide/display WeSelect based on applyTo", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`
                <WeSelect applyTo="'.my-custom-class'">
                    <WeSelectItem classAction="'a'">A</WeSelectItem>
                    <WeSelectItem classAction="'b'">B</WeSelectItem>
                </WeSelect>`,
        });
        const { getEditor } = await setupWebsiteBuilder(
            `<div class="parent-target"><div class="child-target b">b</div></div>`
        );
        const editor = getEditor();
        await contains(":iframe .parent-target").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target b">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
        expect(".options-container button.dropdown-toggle").toHaveCount(0);

        await contains("[data-class-action='my-custom-class']").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target b my-custom-class">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").toHaveClass("active");
        expect(".options-container button.dropdown-toggle").toHaveCount(1);
        await runAllTimers();
        expect(".options-container button.dropdown-toggle").toHaveText("B");
    });

    test("hide/display WeSelectItem base on applyTo", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`
                <WeSelect>
                    <WeSelectItem classAction="'a'">A</WeSelectItem>
                    <WeSelectItem applyTo="'.my-custom-class'" classAction="'b'">B</WeSelectItem>
                    <WeSelectItem classAction="'c'">C</WeSelectItem>
                </WeSelect>`,
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
        expect(".options-container button.dropdown-toggle").toHaveCount(1);
        await contains(".options-container button.dropdown-toggle").click();
        expect(queryAllTexts(".o-dropdown--menu div")).toEqual(["A", "C"]);

        await contains("[data-class-action='my-custom-class']").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target my-custom-class">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").toHaveClass("active");
        await contains(".options-container button.dropdown-toggle").click();
        expect(queryAllTexts(".o-dropdown--menu div")).toEqual(["A", "B", "C"]);
    });

    test("hide/display WeSelect base on applyTo in WeSelectItem", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`
                <WeSelect>
                    <WeSelectItem applyTo="'.my-custom-class'" classAction="'a'">A</WeSelectItem>
                </WeSelect>`,
        });
        await setupWebsiteBuilder(
            `<div class="parent-target"><div class="child-target b">b</div></div>`
        );
        await contains(":iframe .parent-target").click();
        expect(".options-container button.dropdown-toggle").not.toBeVisible();

        await contains("[data-class-action='my-custom-class']").click();
        expect(".options-container button.dropdown-toggle").toBeVisible();
    });
});
describe("WeColorpicker", () => {
    test("should apply color to the editing element", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<WeColorpicker/>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        await click(".o-overlay-item [data-color='o-color-1']");
        expect(":iframe .test-options-target").toHaveClass("test-options-target bg-o-color-1");
    });
    test("hide/display base on applyTo", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`<WeColorpicker applyTo="'.my-custom-class'"/>`,
        });
        const { getEditor } = await setupWebsiteBuilder(
            `<div class="parent-target"><div class="child-target b">b</div></div>`
        );
        const editor = getEditor();
        await contains(":iframe .parent-target").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target b">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
        expect(".options-container .o_we_color_preview").toHaveCount(0);

        await contains("[data-class-action='my-custom-class']").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target b my-custom-class">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").toHaveClass("active");
        expect(".options-container .o_we_color_preview").toHaveCount(1);
    });
});
describe("WeCheckbox", () => {
    test("Click on checkbox", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<WeCheckbox classAction="'checkbox-action'"/>`,
        });
        const { getEditor } = await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        const editor = getEditor();

        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
        expect(editor.editable).toHaveInnerHTML(`<div class="test-options-target">b</div>`);

        await contains(".o-checkbox").click();
        expect(".o-checkbox .form-check-input:checked").toHaveCount(1);
        expect(editor.editable).toHaveInnerHTML(
            `<div class="test-options-target checkbox-action">b</div>`
        );

        await contains(".o-checkbox").click();
        expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
        expect(editor.editable).toHaveInnerHTML(`<div class="test-options-target">b</div>`);
    });
    test("hide/display base on applyTo", async () => {
        addOption({
            selector: ".parent-target",
            template: xml`<WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
        });
        addOption({
            selector: ".parent-target",
            template: xml`<WeCheckbox classAction="'checkbox-action'" applyTo="'.my-custom-class'"/>`,
        });
        const { getEditor } = await setupWebsiteBuilder(
            `<div class="parent-target"><div class="child-target b">b</div></div>`
        );
        const editor = getEditor();

        await contains(":iframe .parent-target").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target b">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
        expect(".options-container .o-checkbox").toHaveCount(0);

        await contains("[data-class-action='my-custom-class']").click();
        expect(editor.editable).toHaveInnerHTML(
            `<div class="parent-target"><div class="child-target b my-custom-class">b</div></div>`
        );
        expect("[data-class-action='my-custom-class']").toHaveClass("active");
        expect(".options-container .o-checkbox").toHaveCount(1);
    });
});
describe("dependencies", () => {
    test("a button should not be visible if its dependency isn't (with undo)", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`
                <WeButton attributeAction="'my-attribute1'" attributeActionValue="'x'" id="'id1'">b1</WeButton>
                <WeButton attributeAction="'my-attribute1'" attributeActionValue="'y'"  id="'id2'">b2</WeButton>
                <WeButton attributeAction="'my-attribute2'" attributeActionValue="'1'" dependencies="'id1'">b3</WeButton>
                <WeButton attributeAction="'my-attribute2'" attributeActionValue="'2'" dependencies="'id2'">b4</WeButton>
            `,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        setSelection({
            anchorNode: queryFirst(":iframe .test-options-target").childNodes[0],
            anchorOffset: 0,
        });
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toBeDisplayed();
        await contains(
            "[data-attribute-action='my-attribute1'][data-attribute-action-value='x']"
        ).click();
        expect(":iframe .test-options-target").toHaveAttribute("my-attribute1", "x");
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toBeDisplayed();
        await contains(
            "[data-attribute-action='my-attribute1'][data-attribute-action-value='y']"
        ).click();
        expect(":iframe .test-options-target").toHaveAttribute("my-attribute1", "y");
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).toBeDisplayed();
        await contains(".fa-undo").click();
        expect(":iframe .test-options-target").toHaveAttribute("my-attribute1", "x");
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toBeDisplayed();
        await contains(".fa-undo").click();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toBeDisplayed();
    });
    test("a button should not be visible if the dependency is active", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`
                <WeButton attributeAction="'my-attribute1'" attributeActionValue="'x'" id="'id1'">b1</WeButton>
                <WeButton attributeAction="'my-attribute2'" attributeActionValue="'1'" dependencies="'!id1'">b3</WeButton>
            `,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).toBeDisplayed();
        await contains(
            "[data-attribute-action='my-attribute1'][data-attribute-action-value='x']"
        ).click();
        expect(":iframe .test-options-target").toHaveAttribute("my-attribute1", "x");
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toBeDisplayed();
    });
    test("a button should not be visible if the dependency is active (when a dependency is added after a dependent)", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`
                <WeButton attributeAction="'my-attribute2'" attributeActionValue="'1'" dependencies="'id'">b1</WeButton>
                <WeButton attributeAction="'my-attribute2'" attributeActionValue="'2'" dependencies="'!id'">b2</WeButton>
                <WeRow label="'dependency'">
                    <WeButton attributeAction="'my-attribute1'" attributeActionValue="'x'" id="'id'">b3</WeButton>
                </WeRow>
            `,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).toBeDisplayed();
        await contains(
            "[data-attribute-action='my-attribute1'][data-attribute-action-value='x']"
        ).click();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).toBeDisplayed();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toBeDisplayed();
    });
});
