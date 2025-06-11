import { describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, clear, click, fill, queryFirst } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { delay } from "@web/core/utils/concurrency";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "../../website_helpers";

defineWebsiteModels();

test("should get the initial value of the input", async () => {
    addActionOption({
        customAction: {
            getValue: ({ editingElement }) => editingElement.innerHTML,
            apply: ({ params }) => {
                expect.step(`customAction ${params}`);
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderNumberInput action="'customAction'"/>`,
    });
    await setupWebsiteBuilder(`
                <div class="test-options-target">10</div>
            `);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    const input = queryFirst(".options-container input");
    expect(input).toHaveValue("10");
});
test("hide/display base on applyTo", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderNumberInput applyTo="'.my-custom-class'" action="'customAction'"/>`,
    });
    addActionOption({
        customAction: {
            getValue: () => "10",
        },
    });

    const { getEditableContent } = await setupWebsiteBuilder(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target o-paragraph">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target o-paragraph my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(1);
    expect("[data-action-id='customAction'] input").toHaveValue("10");
});
test("input with classAction and styleAction", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderNumberInput classAction="'testAction'" styleAction="'--custom-property'"/>`,
    });
    await setupWebsiteBuilder(`
                <div class="test-options-target">10</div>
            `);
    await contains(":iframe .test-options-target").click();
    await click(".options-container input");
    await fill(2);
    expect(":iframe .test-options-target").toHaveStyle({
        "--custom-property": "2",
    });
});

describe("default value", () => {
    test("should use the default value when there is no value onChange", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ value }) => {
                    expect.step(`customAction ${value}`);
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'" default="20"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        const input = queryFirst(".options-container input");
        input.value = "";
        input.dispatchEvent(new Event("input"));
        await delay();
        input.dispatchEvent(new Event("change"));
        await delay();
        expect.verifySteps(["customAction ", "customAction 20"]);
        expect(input).toHaveValue("20");
    });
    test("clear BuilderNumberInput without default value", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ editingElement, value }) => {
                    editingElement.innerHTML = value;
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'" />`,
        });
        await setupWebsiteBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        expect("[data-action-id='customAction'] input").toHaveValue("10");

        await clear();
        await click(".options-container");
        expect("[data-action-id='customAction'] input").toHaveValue("");
        expect(":iframe .test-options-target").toHaveInnerHTML("");
    });
    test("clear BuilderNumberInput with default value", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ editingElement, value }) => {
                    editingElement.innerHTML = value;
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'" default="1"/>`,
        });
        await setupWebsiteBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        expect("[data-action-id='customAction'] input").toHaveValue("10");

        await clear();
        await click(".options-container");
        expect("[data-action-id='customAction'] input").toHaveValue("1");
        expect(":iframe .test-options-target").toHaveInnerHTML("1");
    });
});
describe("operations", () => {
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
            template: xml`<BuilderNumberInput action="'customAction'"/>`,
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
            template: xml`<BuilderNumberInput action="'customAction'"/>`,
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
    test("should commit changes after an undo", async () => {
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
            template: xml`<BuilderNumberInput action="'customAction'"/>`,
        });
        await setupWebsiteBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click(".options-container input");
        await fill(2);
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
        await click(document.body);
        expect.verifySteps(["customAction 102", "customAction 102"]);
        await animationFrame();
        click(".o-snippets-top-actions .fa-undo");
        await animationFrame();
        expect(":iframe .test-options-target").toHaveInnerHTML("10");
        await click(".options-container input");
        await fill("2");
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
        await click(document.body);
        expect.verifySteps(["customAction 102", "customAction 102"]);
    });
    test("should not commit on input if no preview", async () => {
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
            template: xml`<BuilderNumberInput action="'customAction'" preview="false"/>`,
        });
        await setupWebsiteBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click(".options-container input");
        await fill(2);
        expect(":iframe .test-options-target").toHaveInnerHTML("10");
        await click(document.body);
        expect.verifySteps(["customAction 102"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
    });
});
describe("keyboard triggers", () => {
    test("input should step up or down from by the step prop", async () => {
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
            template: xml`<BuilderNumberInput action="'customAction'" step="2"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();

        // simulate arrow up
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("12");

        // simulate arrow down
        await contains(".options-container input").keyDown("ArrowDown");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("10");

        expect.verifySteps(["customAction 12", "customAction 10"]);
    });
    test("multi values: apply change on each value with up or down", async () => {
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
            template: xml`<BuilderNumberInput action="'customAction'" composable="true"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target">10 4 0</div>
        `);
        await contains(":iframe .test-options-target").click();

        // simulate arrow up
        await contains(".options-container input").focus();
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("11 5 1");

        // simulate arrow down
        await contains(".options-container input").keyDown("ArrowDown");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("10 4 0");

        expect.verifySteps(["customAction 11 5 1", "customAction 10 4 0"]);
    });
    test("up on empty BuilderNumberInput gives 1", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.dataset.number,
                apply: ({ editingElement, value }) => {
                    editingElement.dataset.number = value;
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'" />`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">Non empty div.</div>`);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        expect("[data-action-id='customAction'] input").toHaveValue("");

        await contains("[data-action-id='customAction'] input").keyDown("ArrowUp");
        expect("[data-action-id='customAction'] input").toHaveValue("1");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "1");
    });
    test("down on empty BuilderNumberInput gives -1", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.dataset.number,
                apply: ({ editingElement, value }) => {
                    editingElement.dataset.number = value;
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'" />`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">Non empty div.</div>`);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        expect("[data-action-id='customAction'] input").toHaveValue("");

        await contains("[data-action-id='customAction'] input").keyDown("ArrowDown");
        await animationFrame();
        expect("[data-action-id='customAction'] input").toHaveValue("-1");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "-1");
    });
    test("apply preview on keydown and debounce commit operation", async () => {
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
            template: xml`<BuilderNumberInput action="'customAction'"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").focus();
        // Simulate a single keydown hold down for a while.
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime(500); // Default browser delay between 1st & 2nd keydown.
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime();
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("13");
        // 3 previews
        expect.verifySteps(["customAction 11", "customAction 12", "customAction 13"]);
        await advanceTime(560); // Debounce = 550
        // 1 commit
        expect.verifySteps(["customAction 13"]);
    });
});
describe("unit & saveUnit", () => {
    test("should handle unit", async () => {
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
            template: xml`<BuilderNumberInput action="'customAction'" unit="'px'"/>`,
        });
        await setupWebsiteBuilder(`
                    <div class="test-options-target">5px</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("5");
        await fill(1);
        expect.verifySteps(["customAction 51px"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("51px");
    });
    test("should handle saveUnit", async () => {
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
            template: xml`<BuilderNumberInput action="'customAction'" unit="'s'" saveUnit="'ms'"/>`,
        });
        await setupWebsiteBuilder(`
                    <div class="test-options-target">5000ms</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("5");
        await fill("7");
        expect.verifySteps(["customAction 57000ms"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("57000ms");
    });
    test("should handle empty saveUnit", async () => {
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
            template: xml`<BuilderNumberInput action="'customAction'" unit="'px'" saveUnit="''"/>`,
        });
        await setupWebsiteBuilder(`
                    <div class="test-options-target">5</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("5");
        await fill(1);
        expect.verifySteps(["customAction 51"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("51");
    });
});
describe("sanitized values", () => {
    test("don't allow multi values by default", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ editingElement, value }) => {
                    editingElement.innerHTML = value;
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("33 4 0", { instantly: true });
        expect(".options-container input").toHaveValue("33");
        expect(":iframe .test-options-target").toHaveInnerHTML("33");
    });
    test("use min when the given value is smaller", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ value }) => {
                    expect.step(`customAction ${value}`);
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'" min="0"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("-1", { instantly: true });
        expect.verifySteps(["customAction ", "customAction 0"]); // input, change
        expect(".options-container input").toHaveValue("0");
    });
    test("use max when the given value is bigger", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ value }) => {
                    expect.step(`customAction ${value}`);
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'" max="10"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target">3</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("11", { instantly: true });
        await animationFrame();
        expect.verifySteps(["customAction ", "customAction 10"]); // input, change
        expect(".options-container input").toHaveValue("10");
    });
    test("multi values: trailing space in BuilderNumberInput is ignored", async () => {
        addActionOption({
            customAction: {
                getValue: ({ editingElement }) => editingElement.innerHTML,
                apply: ({ value }) => {
                    expect.step(`customAction ${value}`);
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput action="'customAction'" composable="true"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").fill("3 4 5 ", { instantly: true });
        expect.verifySteps(["customAction 3 4 5", "customAction 3 4 5"]); // input, change
        expect(".options-container input").toHaveValue("3 4 5");
    });
    test("after input, displayed value is cleaned to match only numbers", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput dataAttributeAction="'number'"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit(" a&$*+>");
        expect(".options-container input").toHaveValue("");
        expect(":iframe .test-options-target").not.toHaveAttribute("data-number");
    });
    test("after copy / pasting, displayed value is cleaned to match only numbers", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput dataAttributeAction="'number'"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit(" a&$*-3+>", { instantly: true });
        expect(".options-container input").toHaveValue("-3");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "-3");
    });
    test("accept decimal numbers", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput dataAttributeAction="'number'"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("3.3");
        expect(".options-container input").toHaveValue("3.3");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "3.3");
    });
    test("BuilderNumberInput transforms , into .", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderNumberInput dataAttributeAction="'number'"/>`,
        });
        await setupWebsiteBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("3,3");
        expect(".options-container input").toHaveValue("3.3");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "3.3");
    });
});
