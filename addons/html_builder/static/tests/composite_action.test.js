import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { Builder } from "@html_builder/builder";
import { BuilderAction } from "@html_builder/core/builder_action";
import { SavePlugin } from "@html_builder/core/save_plugin";
import { describe, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

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

test("composite action should use the first getValue", async () => {
    class Action1 extends BuilderAction {
        static id = "action1";
        setup() {
            this.data = { name: "first action" };
        }
        getValue() {
            return this.data.name;
        }
        apply() {}
    }
    class Action2 extends BuilderAction {
        static id = "action2";
        setup() {
            this.data = { name: "second action" };
        }
        getValue() {
            return this.data.name;
        }
        apply() {}
    }
    addBuilderAction({
        Action1,
        Action2,
    });
    addBuilderOption({
        selector: ".s_test",
        template: xml`
            <BuilderTextInput action="'composite'"
                actionParam="[
                    { action: 'action1' },
                    { action: 'action2' },
                ]"/>`,
    });
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();

    expect("[data-action-id='composite'] input").toHaveValue("first action");
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
    expect("[data-action-id='composite']").not.toHaveClass("active");
    await contains("[data-action-id='composite']").click();
    expect("[data-action-id='composite']").toHaveClass("active");
});

test("applied composite action's with no getPriority implementation is considered the applied option", async () => {
    addBuilderOption({
        selector: ".s_test",
        template: xml`
            <BuilderSelect>
                <BuilderSelectItem
                    action="'composite'"
                    actionParam="[
                        { action: 'dataAttributeAction', actionParam: { mainParam: 'test' } },
                    ]"
                    actionValue="'something'">
                    The Test Option
                </BuilderSelectItem>
            </BuilderSelect>`,
    });
    await setupHTMLBuilder(`<section class="s_test" data-test="something">Test</section>`);
    await contains(":iframe .s_test").click();
    expect(".o_hb_select_wrapper button").toHaveText("The Test Option");
});

test("composite action calls the prepare of its actions", async () => {
    class Action1 extends BuilderAction {
        static id = "action1";
        async prepare({ actionParam, actionValue }) {
            expect.step(`prepare1: ${actionParam.mainParam} ${actionValue}`);
        }
        apply() {}
    }
    class Action2 extends BuilderAction {
        static id = "action2";
        apply() {}
    }
    addBuilderAction({ Action1, Action2 });
    addBuilderOption({
        selector: ".s_test",
        template: xml`
            <BuilderButton
                action="'composite'"
                actionParam="[
                    { action: 'action1', actionParam: { mainParam: 'class1' } },
                    { action: 'action2' },
                ]"
                actionValue="'value'">
                Click
        </BuilderButton>`,
    });
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();
    expect.verifySteps(["prepare1: class1 value"]);
});

test("composite action loads its actions in order and gives each its result", async () => {
    class Action1 extends BuilderAction {
        static id = "action1";
        async load() {
            await new Promise((resolve) => setTimeout(resolve, 10));
            expect.step("load1");
            return "result1";
        }
        apply({ loadResult }) {
            expect.step(`apply1: ${loadResult}`);
        }
    }
    class Action2 extends BuilderAction {
        static id = "action2";
        async load() {
            expect.step("load2");
            return "result2";
        }
        apply({ loadResult }) {
            expect.step(`apply2: ${loadResult}`);
        }
    }
    addBuilderAction({ Action1, Action2 });
    addBuilderOption({
        selector: ".s_test",
        template: xml`
            <BuilderButton
                action="'composite'"
                actionParam="[{ action: 'action1' }, { action: 'action2' }]"
                preview="false">
                Click
        </BuilderButton>`,
    });
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();
    await contains("[data-action-id='composite']").click();
    await expect.waitForSteps(["load1", "load2", "apply1: result1", "apply2: result2"]);
});

test("reloadComposite action saves and reloads the editor", async () => {
    patch(SavePlugin.prototype, {
        async save() {
            expect.step("save");
            await super.save();
        },
    });
    patch(Builder.prototype, {
        setup() {
            super.setup();
            this.editor.config.reloadEditor = async () => expect.step("reload");
        },
    });
    class Action1 extends BuilderAction {
        static id = "action1";
        apply({ editingElement }) {
            editingElement.classList.add("class1");
            expect.step("apply1");
        }
    }
    addBuilderAction({ Action1 });
    addBuilderOption({
        selector: ".s_test",
        template: xml`
            <BuilderButton action="'reloadComposite'" actionParam="[{ action: 'action1' }]">
                Click
            </BuilderButton>`,
    });
    await setupHTMLBuilder(`<section class="s_test">Test</section>`);
    await contains(":iframe .s_test").click();
    await contains("[data-action-id='reloadComposite']").click();
    // No preview: the action is applied only once before the reload.
    await expect.waitForSteps(["apply1", "save", "reload"]);
});
