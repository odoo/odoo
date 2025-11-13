import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expect, test, describe } from "@odoo/hoot";
import {
    animationFrame,
    click,
    press,
    queryAllTexts,
    queryFirst,
    runAllTimers,
    tick,
} from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";

describe.current.tags("desktop");

test("call a specific action with some params and value (BuilderSelectItem)", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ params: { mainParam: testParam }, value }) {
                expect.step(`customAction ${testParam} ${value}`);
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                <BuilderSelect>
                    <BuilderSelectItem action="'customAction'" actionParam="'myParam'" actionValue="'myValue'">MyAction</BuilderSelectItem>
                </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    expect(".popover [data-action-id='customAction']").toHaveText("MyAction");
    await click(".popover [data-action-id='customAction']");
    await animationFrame();
    // The function `apply` should be called twice (on hover (for preview), then, on click).
    expect.verifySteps(["customAction myParam myValue", "customAction myParam myValue"]);
});
test("set the label of the select from the active select item and be updated on undo/redo", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                <BuilderSelect attributeAction="'customAttribute'">
                    <BuilderSelectItem attributeActionValue="null">None</BuilderSelectItem>
                    <BuilderSelectItem attributeActionValue="'a'">A</BuilderSelectItem>
                    <BuilderSelectItem attributeActionValue="'b'">B</BuilderSelectItem>
                </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target" customAttribute="a">x</div>`);
    setSelection({
        anchorNode: queryFirst(":iframe .test-options-target").childNodes[0],
        anchorOffset: 0,
    });
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(".we-bg-options-container .dropdown").toHaveText("A");
    await contains(".we-bg-options-container .dropdown").click();
    await contains(".o-overlay-item [data-attribute-action-value='b']").click();
    expect(".we-bg-options-container .dropdown").toHaveText("B");
    await animationFrame();
    expect(".o-overlay-item [data-attribute-action-value='b']").not.toHaveCount();
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".we-bg-options-container .dropdown").toHaveText("A");
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".we-bg-options-container .dropdown").toHaveText("B");
});
test("consider the priority of the select item", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                <BuilderSelect>
                    <BuilderSelectItem classAction="''">None</BuilderSelectItem>
                    <BuilderSelectItem classAction="'a'">A</BuilderSelectItem>
                    <BuilderSelectItem classAction="'a b'">A B</BuilderSelectItem>
                </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target a">x</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();

    expect(".we-bg-options-container .dropdown").toHaveText("A");
    await contains(".we-bg-options-container .dropdown").click();

    await contains(".o-overlay-item [data-class-action='']").click();
    expect(".we-bg-options-container .dropdown").toHaveText("None");
    await contains(".we-bg-options-container .dropdown").click();

    await contains(".o-overlay-item [data-class-action='a b']").click();
    expect(".we-bg-options-container .dropdown").toHaveText("A B");
});
test("hide/display BuilderSelect based on applyTo", async () => {
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
                    <BuilderSelect applyTo="'.my-custom-class'">
                        <BuilderSelectItem classAction="'a'">A</BuilderSelectItem>
                        <BuilderSelectItem classAction="'b'">B</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="parent-target"><div class="child-target b">b</div></div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect(".options-container button.dropdown-toggle").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect(".options-container button.dropdown-toggle").toHaveCount(1);
    await runAllTimers();
    expect(".options-container button.dropdown-toggle").toHaveText("B");
});

test("hide/display BuilderSelectItem base on applyTo", async () => {
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
                    <BuilderSelect>
                        <BuilderSelectItem classAction="'a'">A</BuilderSelectItem>
                        <BuilderSelectItem applyTo="'.my-custom-class'" classAction="'b'">B</BuilderSelectItem>
                        <BuilderSelectItem classAction="'c'">C</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect(".options-container button.dropdown-toggle").toHaveCount(1);
    await contains(".options-container button.dropdown-toggle").click();
    expect(queryAllTexts(".o-dropdown--menu div.o-dropdown-item")).toEqual(["A", "C"]);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    await contains(".options-container button.dropdown-toggle").click();
    expect(queryAllTexts(".o-dropdown--menu div.o-dropdown-item")).toEqual(["A", "B", "C"]);
});

test("hide/display BuilderSelect base on applyTo in BuilderSelectItem", async () => {
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
                    <BuilderSelect>
                        <BuilderSelectItem applyTo="'.my-custom-class'" classAction="'a'">A</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="parent-target"><div class="child-target b">b</div></div>`);
    await contains(":iframe .parent-target").click();
    expect(".options-container button.dropdown-toggle").not.toBeVisible();

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container button.dropdown-toggle").toBeVisible();
});

test("use BuilderSelect with styleAction", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`
                    <BuilderSelect styleAction="'border-style'">
                        <BuilderSelectItem styleActionValue="'dotted'">dotted</BuilderSelectItem>
                        <BuilderSelectItem styleActionValue="'inset'">inset</BuilderSelectItem>
                        <BuilderSelectItem styleActionValue="'none'">none</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(`<div class="parent-target">b</div>`);
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(".we-bg-options-container .dropdown").toHaveText("none");

    await contains(".options-container button.dropdown-toggle").click();
    expect(queryAllTexts(".o-dropdown--menu div.o-dropdown-item")).toEqual([
        "dotted",
        "inset",
        "none",
    ]);

    await contains(".o-dropdown--menu div.o-dropdown-item:contains(dotted)").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target" style="border-style: dotted;">b</div>`
    );
    expect(".we-bg-options-container .dropdown").toHaveText("dotted");
});
test("do not put inline style on an element which already has this style through css stylesheets", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test";
            static template = xml`
                    <BuilderSelect applyTo="'hr'" styleAction="'border-top-style'">
                        <BuilderSelectItem styleActionValue="'dotted'">dotted</BuilderSelectItem>
                        <BuilderSelectItem styleActionValue="'inset'">inset</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`
            <div class="test">
                <hr class="w-100">
            </div>
    `);
    await contains(":iframe .test").click();
    expect(".we-bg-options-container .dropdown").toHaveText("inset");
    await contains(".we-bg-options-container .dropdown").click();
    await contains(".o-dropdown--menu div.o-dropdown-item:contains('dotted')").click();
    expect(":iframe hr").toHaveStyle({ "border-top-style": "dotted" });
    await contains(".we-bg-options-container .dropdown").click();
    await contains(".o-dropdown--menu div.o-dropdown-item:contains('inset')").click();
    expect(":iframe hr").not.toHaveStyle("border-top-style", { inline: true });
});
test("revert a preview when cancelling a BuilderSelect by clicking outside of it", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test";
            static template = xml`
                    <BuilderSelect dataAttributeAction="'choice'">
                        <BuilderSelectItem dataAttributeActionValue="'0'">0</BuilderSelectItem>
                        <BuilderSelectItem dataAttributeActionValue="'1'">1</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="test">Test</div>`);
    await contains(":iframe .test").click();
    expect(":iframe .test").not.toHaveAttribute("data-choice");
    await contains(".we-bg-options-container .dropdown").click();
    await contains(".o-dropdown--menu div.o-dropdown-item:contains('0')").hover();
    expect(":iframe .test").toHaveAttribute("data-choice", "0");
    await click(".we-bg-options-container");
    expect(":iframe .test").not.toHaveAttribute("data-choice");
});
test("revert a preview when cancelling a BuilderSelect with escape", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test";
            static template = xml`
                    <BuilderSelect dataAttributeAction="'choice'">
                        <BuilderSelectItem dataAttributeActionValue="'0'">0</BuilderSelectItem>
                        <BuilderSelectItem dataAttributeActionValue="'1'">1</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="test">Test</div>`);
    await contains(":iframe .test").click();
    expect(":iframe .test").not.toHaveAttribute("data-choice");
    await contains(".we-bg-options-container .dropdown").click();
    await contains(".o-dropdown--menu div.o-dropdown-item:contains('0')").hover();
    expect(":iframe .test").toHaveAttribute("data-choice", "0");
    await press("escape");
    expect(":iframe .test").not.toHaveAttribute("data-choice");
});
test("preview when cycling through options with the keyboard", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test";
            static template = xml`
                    <BuilderSelect dataAttributeAction="'choice'">
                        <BuilderSelectItem dataAttributeActionValue="'0'">0</BuilderSelectItem>
                        <BuilderSelectItem dataAttributeActionValue="'1'">1</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="test">Test</div>`);
    await contains(":iframe .test").click();
    expect(":iframe .test").not.toHaveAttribute("data-choice");
    await contains(".we-bg-options-container .dropdown").press("enter");
    await press("arrowdown");
    expect(":iframe .test").toHaveAttribute("data-choice", "0");
});
test("revert a preview selected with the keyboard when cancelling with escape", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test";
            static template = xml`
                    <BuilderSelect dataAttributeAction="'choice'">
                        <BuilderSelectItem dataAttributeActionValue="'0'">0</BuilderSelectItem>
                        <BuilderSelectItem dataAttributeActionValue="'1'">1</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="test">Test</div>`);
    await contains(":iframe .test").click();
    expect(":iframe .test").not.toHaveAttribute("data-choice");
    await contains(".we-bg-options-container .dropdown").press("enter");
    await press("arrowdown");
    expect(".o-dropdown--menu div.o-dropdown-item:contains('0')").toBeFocused();
    await press("escape");
    await tick();
    expect(":iframe .test").not.toHaveAttribute("data-choice");
});

test("isApplied shouldn't be called when the element is removed from the DOM", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            isApplied({ editingElement: el }) {
                expect(el.isConnected).toBe(true);
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test";
            static template = xml`
                    <BuilderSelect action="'customAction'">
                        <BuilderSelectItem actionParam="'0'">0</BuilderSelectItem>
                        <BuilderSelectItem actionParam="'1'">1</BuilderSelectItem>
                    </BuilderSelect>`;
        }
    );
    await setupHTMLBuilder(`<div class="test">Test</div>`);
    await contains(":iframe .test").click();
    await contains(".fa-trash ").click();
    expect(":iframe .test").toHaveCount(0);
});
