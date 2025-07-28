import {
    addBuilderPlugin,
    addBuilderOption,
    addBuilderAction,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { expect, test, describe } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("Undo/Redo correctly restores the stored container target", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ editingElement }) {
                editingElement.remove();
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton action="'customAction'">Test</BuilderButton>`;
        }
    );
    await setupHTMLBuilder(`
        <div data-name="Target 1" class="test-options-target target1">
            Homepage
        </div>
        <div data-name="Target 2" class="test-options-target target2">
            Homepage2
        </div>

    `);

    await contains(":iframe .target1").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains("[data-action-id='customAction']").click();
    await contains(":iframe .target2").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");

    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveCount(0);
});

test("Undo/Redo multiple actions always restores the action container target", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ editingElement }) {
                editingElement.classList.add("test");
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton action="'customAction'">Test</BuilderButton>`;
        }
    );
    await setupHTMLBuilder(`
        <div data-name="Target 1" class="test-options-target target1">
            Homepage
        </div>
        <div data-name="Target 2" class="test-options-target target2">
            Homepage2
        </div>

    `);

    await contains(":iframe .target1").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains("[data-action-id='customAction']").click();
    await contains(":iframe .target2").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    await contains("[data-action-id='customAction']").click();
    expect(":iframe .test-options-target.test").toHaveCount(2);
    // Undo everything.
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    expect(":iframe .test-options-target.test").toHaveCount(0);
    // Redo everything.
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    expect(":iframe .test-options-target.test").toHaveCount(2);
});

test("Undo/Redo an action that activates another target restores the old one on undo and the new one on redo", async () => {
    let editor;
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ editingElement }) {
                editingElement.classList.add("test");
                editor.shared.builderOptions.setNextTarget(editingElement.nextElementSibling);
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton action="'customAction'">Test</BuilderButton>`;
        }
    );
    const { getEditor } = await setupHTMLBuilder(`
        <div data-name="Target 1" class="test-options-target target1">
            Homepage
        </div>
        <div data-name="Target 2" class="test-options-target target2">
            Homepage2
        </div>

    `);
    editor = getEditor();

    await contains(":iframe .target1").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains("[data-action-id='customAction']").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    // Undo everything.
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
});

test("Undo/Redo an action that deactivates the containers restores the old one on undo and deactivates again on redo", async () => {
    let editor;
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ editingElement }) {
                editingElement.classList.add("test");
                editor.shared.builderOptions.setNextTarget(false);
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton action="'customAction'">Test</BuilderButton>`;
        }
    );
    const { getEditor } = await setupHTMLBuilder(`
        <div data-name="Target 1" class="test-options-target target1">
            Homepage
        </div>
    `);
    editor = getEditor();

    await contains(":iframe .target1").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains("[data-action-id='customAction']").click();
    expect(".options-container").toHaveCount(0);
    expect("button[data-name='blocks']").toHaveClass("active");
    // Undo everything.
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveCount(0);
    expect("button[data-name='blocks']").toHaveClass("active");
});

test("Containers fallback to a valid ancestor if the target disappears and restore it on undo", async () => {
    addBuilderAction({
        targetAction: class extends BuilderAction {
            static id = "targetAction";
            apply({ editingElement }) {
                editingElement.remove();
            }
        },
        ancestorAction: class extends BuilderAction {
            static id = "ancestorAction";
            apply({ editingElement }) {
                editingElement.remove();
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton action="'targetAction'">Test</BuilderButton>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-ancestor";
            static template = xml`<BuilderButton action="'ancestorAction'">Ancestor selected</BuilderButton>`;
        }
    );
    await setupHTMLBuilder(`
        <div data-name="Ancestor" class="test-ancestor">
            Hey I'm an ancestor
            <div data-name="Target 1" class="test-options-target target1">
                Homepage
            </div>
        </div>

    `);

    await contains(":iframe .target1").click();
    expect(".options-container[data-container-title='Ancestor']").toHaveCount(1);
    expect(".options-container[data-container-title='Target 1']").toHaveCount(1);
    await contains("[data-action-id='targetAction']").click();
    expect(".options-container[data-container-title='Ancestor']").toHaveCount(1);
    expect(".options-container[data-container-title='Target 1']").toHaveCount(0);
    expect("[data-action-id='ancestorAction']").toHaveCount(1);

    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container[data-container-title='Ancestor']").toHaveCount(1);
    expect(".options-container[data-container-title='Target 1']").toHaveCount(1);
});

test("Do not activate/update containers if the element clicked is excluded", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderButton classAction="'test'">Test</BuilderButton>`;
        }
    );
    await setupHTMLBuilder(`
        <div data-name="Target 1" class="test-options-target target1 o_we_no_overlay">
            Homepage
        </div>
        <div data-name="Target 2" class="test-options-target target2">
            Homepage2
        </div>

    `);

    await contains(":iframe .target1").click();
    expect(".options-container").toHaveCount(0);
    await contains(":iframe .target2").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    expect(".options-container [data-class-action='test']").toHaveCount(1);
    await contains(":iframe .target1").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
});

test("Do not show parent container for no_parent_containers targets", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            no_parent_containers: ".test-child-target",
        };
    }
    addBuilderPlugin(TestPlugin);
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-parent-target";
            static template = xml`<BuilderButton classAction="'test'">Test</BuilderButton>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-child-target";
            static template = xml`<BuilderButton classAction="'test'">Test</BuilderButton>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-grand-child-target";
            static template = xml`<BuilderButton classAction="'test'">Test</BuilderButton>`;
        }
    );
    await setupHTMLBuilder(`
        <div data-name="Parent" class="test-parent-target">
            Parent
            <div data-name="Child" class="test-child-target">
                Child
                <div data-name="Grand-child" class="test-grand-child-target">
                    Grand-Child
                </div>
            </div>
        </div>
    `);

    await contains(":iframe .test-child-target").click();
    expect(".options-container").toHaveCount(1);
    expect(".options-container").toHaveAttribute("data-container-title", "Child");
    // Try with several layers
    await contains(":iframe .test-grand-child-target").click();
    expect(".options-container").toHaveCount(2);
    expect(".options-container:eq(0)").toHaveAttribute("data-container-title", "Child");
    expect(".options-container:eq(1)").toHaveAttribute("data-container-title", "Grand-child");
    // Make sure the parent's options still appear for itself.
    await contains(":iframe .test-parent-target").click();
    expect(".options-container").toHaveCount(1);
    expect(".options-container").toHaveAttribute("data-container-title", "Parent");
});
