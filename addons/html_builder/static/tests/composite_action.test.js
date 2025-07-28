import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { describe, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";

// TODO: test composite with each spec: prepare, load, getValue
// TODO: test reloadComposite

describe.current.tags("desktop");

test("can call 2 separate actions with composite action", async () => {
    class Action1 extends BuilderAction {
        static id = "action1";
        isApplied({ editingElement, params: { mainParam: cls } }) {
            return editingElement.classList.contains(cls);
        }
        apply({ editingElement, params: { mainParam: cls } }) {
            editingElement.classList.toggle(cls);
            expect.step(`action1: ${cls}`);
        }
    }
    class Action2 extends BuilderAction {
        static id = "action2";
        isApplied({ editingElement, params: { mainParam: cls } }) {
            return editingElement.classList.contains(cls);
        }
        apply({ editingElement, params: { mainParam: cls } }) {
            editingElement.classList.toggle(cls);
            expect.step(`action2: ${cls}`);
        }
    }
    addBuilderAction({
        Action1,
        Action2,
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".s_test";
            static template = xml`
            <BuilderButton
                    action="'composite'"
                    actionParam="[
                        { action: 'action1', actionParam: { mainParam: 'class1' } },
                        { action: 'action2', actionParam: { mainParam: 'class2' } },
                    ]">
                Click
            </BuilderButton>`;
        }
    );
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
    class Action1 extends BuilderAction {
        static id = "action1";
        isApplied({ editingElement, params: { mainParam: cls } }) {
            return editingElement.classList.contains(cls);
        }
        apply({ editingElement, params: { mainParam: cls } }) {
            editingElement.classList.toggle(cls);
            expect.step(`action1: ${cls}`);
        }
    }
    addBuilderAction({
        Action1,
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".s_test";
            static template = xml`
            <BuilderButton
                    action="'composite'"
                    actionParam="[
                        { action: 'action1', actionParam: { mainParam: 'class1' } },
                        { action: 'action1', actionParam: { mainParam: 'class2' } },
                    ]">
                Click
            </BuilderButton>`;
        }
    );
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

test("composite action's isApplied returns false if no action defined it", async () => {
    class Action1 extends BuilderAction {
        static id = "action1";
        apply({ params: { mainParam: cls } }) {
            expect.step(`action: ${cls}`);
        }
    }
    addBuilderAction({
        Action1,
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".s_test";
            static template = xml`
            <BuilderButton
                    action="'composite'"
                    actionParam="[
                        { action: 'action1', actionParam: { mainParam: 'class1' } },
                        { action: 'action1', actionParam: { mainParam: 'class2' } },
                    ]">
                Click
            </BuilderButton>`;
        }
    );
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();
    expect("[data-action-id='composite']").not.toHaveClass("active");
    await contains("[data-action-id='composite']").click();
    expect("[data-action-id='composite']").not.toHaveClass("active");
    expect.verifySteps([
        "action: class1", // preview
        "action: class2", // preview
        "action: class1", // apply
        "action: class2", // apply
    ]);
});

test("composite action's isApplied returns true if at least one action defined it", async () => {
    class Action1 extends BuilderAction {
        static id = "action1";
        apply() {}
    }
    class Action2 extends BuilderAction {
        static id = "action2";
        isApplied({ editingElement, params: { mainParam: cls } }) {
            return editingElement.classList.contains(cls);
        }
        apply({ editingElement, params: { mainParam: cls } }) {
            editingElement.classList.add(cls);
        }
    }
    addBuilderAction({
        Action1,
        Action2,
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".s_test";
            static template = xml`
            <BuilderButton
                    action="'composite'"
                    actionParam="[
                        { action: 'action1', actionParam: { mainParam: 'class1' } },
                        { action: 'action2', actionParam: { mainParam: 'class2' } },
                    ]">
                Click
            </BuilderButton>`;
        }
    );
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();
    expect("[data-action-id='composite']").not.toHaveClass("active");
    await contains("[data-action-id='composite']").click();
    expect("[data-action-id='composite']").toHaveClass("active");
});
