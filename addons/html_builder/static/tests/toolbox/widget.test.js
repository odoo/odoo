import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, fill, hover, queryFirst } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../helpers";

defineWebsiteModels();

describe("WeButton", () => {
    test("call a specific action with some params and value", async () => {
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    apply: ({ param, value }) => {
                        expect.step(`customAction ${param} ${value}`);
                    },
                },
            },
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
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    apply: ({ editingElement }) => {
                        expect.step(`customAction`);
                        editingElement.innerHTML = "c";
                    },
                },
            },
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
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    apply: ({ editingElement }) => {
                        expect.step(`customAction`);
                        editingElement.innerHTML = "c";
                    },
                },
            },
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
});
describe("WeButtonGroup", () => {
    test("change the editingElement of sub widget through `applyTo` prop", async () => {
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    apply: ({ editingElement }) => {
                        expect.step(`customAction ${editingElement.className}`);
                    },
                },
            },
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
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    apply: ({ param }) => {
                        expect.step(`customAction ${param}`);
                    },
                },
            },
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
});
describe("WeNumberInput", () => {
    test("should get the initial value of the input", async () => {
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    getValue: ({ editingElement }) => {
                        return editingElement.innerHTML;
                    },
                    apply: ({ param }) => {
                        expect.step(`customAction ${param}`);
                    },
                },
            },
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
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    getValue: ({ editingElement }) => {
                        return editingElement.innerHTML;
                    },
                    apply: ({ editingElement, value }) => {
                        expect.step(`customAction ${value}`);
                        editingElement.innerHTML = value;
                    },
                },
            },
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
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    getValue: ({ editingElement }) => {
                        return editingElement.innerHTML;
                    },
                    apply: ({ editingElement, value }) => {
                        expect.step(`customAction ${value}`);
                        editingElement.innerHTML = value;
                    },
                },
            },
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
});
describe("WeSelectItem", () => {
    test("call a specific action with some params and value (WeSelectItem)", async () => {
        addOption({
            selector: ".test-options-target",
            actions: {
                customAction: {
                    apply: ({ param, value }) => {
                        expect.step(`customAction ${param} ${value}`);
                    },
                },
            },
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
    test("set the label of the select from the active select item", async () => {
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
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".we-bg-options-container .dropdown").toHaveText("A");
        await click(".we-bg-options-container .dropdown");
        await animationFrame();
        await click(".o-overlay-item [data-attribute-action-value-id='b']");
        expect(".we-bg-options-container .dropdown").toHaveText("B");
        await animationFrame();
        expect(".o-overlay-item [data-attribute-action-value-id='b']").not.toBeDisplayed();
    });
});
