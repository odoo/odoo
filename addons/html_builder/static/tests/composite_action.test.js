import { describe, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";

describe.current.tags("desktop");
test("can call 2 separate actions with composite action", async () => {
    addBuilderAction({
        action1: {
            isApplied: ({ editingElement, param: { mainParam: cls } }) =>
                editingElement.classList.contains(cls),
            apply: ({ editingElement, param: { mainParam: cls } }) => {
                editingElement.classList.toggle(cls);
                expect.step(`action1: ${cls}`);
            },
        },
        action2: {
            isApplied: ({ editingElement, param: { mainParam: cls } }) =>
                editingElement.classList.contains(cls),
            apply: ({ editingElement, param: { mainParam: cls } }) => {
                editingElement.classList.toggle(cls);
                expect.step(`action2: ${cls}`);
            },
        },
    });
    addBuilderOption({
        selector: ".s_test",
        template: xml`
            <BuilderButton
                    action="'composite'"
                    actionParam="[
                        { action: 'action1', actionParam: { mainParam: 'class1' } },
                        { action: 'action2', actionParam: { mainParam: 'class2' } },
                    ]">
                Click
            </BuilderButton>`,
    });
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();
    await contains("[data-action-id='composite']").click();
    expect(":iframe .s_test").toHaveClass("class1 class2");
    expect.verifySteps([
        "action1: class1", // preview
        "action2: class2", // preview
        "action1: class1", // apply
        "action2: class2", // apply
    ]);
    await contains("[data-action-id='composite']").click();
    expect.verifySteps(["action1: class1", "action2: class2"]); // clean
});

test("can call the same action twice with composite action", async () => {
    addBuilderAction({
        action1: {
            isApplied: ({ editingElement, param: { mainParam: cls } }) =>
                editingElement.classList.contains(cls),
            apply: ({ editingElement, param: { mainParam: cls } }) => {
                editingElement.classList.toggle(cls);
                expect.step(`action1: ${cls}`);
            },
        },
    });
    addBuilderOption({
        selector: ".s_test",
        template: xml`
            <BuilderButton
                    action="'composite'"
                    actionParam="[
                        { action: 'action1', actionParam: { mainParam: 'class1' } },
                        { action: 'action1', actionParam: { mainParam: 'class2' } },
                    ]">
                Click
            </BuilderButton>`,
    });
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();
    await contains("[data-action-id='composite']").click();
    expect(":iframe .s_test").toHaveClass("class1 class2");
    expect.verifySteps([
        "action1: class1", // preview
        "action1: class2", // preview
        "action1: class1", // apply
        "action1: class2", // apply
    ]);
    await contains("[data-action-id='composite']").click();
    expect.verifySteps(["action1: class1", "action1: class2"]); // clean
});

// TODO: test composite with each spec: prepare, load, getValue, isApplied
// TODO: test reloadComposite
