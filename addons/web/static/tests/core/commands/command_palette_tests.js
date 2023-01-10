/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CommandPalette } from "@web/core/commands/command_palette";
import { CommandPaletteDialog } from "@web/core/commands/command_palette_dialog";
import { commandService } from "@web/core/commands/command_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { makeTestEnv } from "../../helpers/mock_env";
import {
    click,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "../../helpers/utils";
import { editSearchBar } from "./command_service_tests";

const { Component, mount, tags } = owl;
const { xml } = tags;

let env;
let target;
let testComponent;
const serviceRegistry = registry.category("services");

const footerTemplate = xml`<span>My footer</span>`;

class TestComponent extends Component {
    get DialogContainer() {
        return registry.category("main_components").get("DialogContainer");
    }
}
TestComponent.template = xml`
  <div>
    <div class="o_dialog_container"/>
    <t t-component="DialogContainer.Component" t-props="DialogContainer.props" />
  </div>
`;

QUnit.module("Command Palette Dialog", {
    async beforeEach() {
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("command", commandService);

        patchWithCleanup(browser, {
            clearTimeout: () => {},
            setTimeout: (later, wait) => {
                later();
            },
        });

        env = await makeTestEnv();
        target = getFixture();
    },
    afterEach() {
        if (testComponent) {
            testComponent.destroy();
        }
    },
});

QUnit.test("empty providers", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const config = {
        providers: [],
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        "No results found"
    );
    assert.strictEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "Search..."
    );
    assert.containsNone(target, ".o_command_palette_footer");
});

QUnit.test("custom empty message", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const emptyMessageByNamespace = {
        default: "Empty Default",
        "@": "Empty @",
        "#": "Empty #",
    };
    const provide = () => [];
    const providers = [
        { namespace: "@", provide },
        { namespace: "#", provide },
    ];
    const config = {
        emptyMessageByNamespace,
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        emptyMessageByNamespace["default"]
    );

    await editSearchBar("@");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        emptyMessageByNamespace["@"]
    );

    await editSearchBar("#");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        emptyMessageByNamespace["#"]
    );
});

QUnit.test("custom placeholder", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const config = {
        placeholder: "placeholder test",
        providers: [],
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "placeholder test"
    );
});

QUnit.test("add a footer", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const config = {
        providers: [],
        footerTemplate,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_footer");
    assert.strictEqual(target.querySelector(".o_command_palette_footer").textContent, "My footer");
});

QUnit.test("command with a Custom Component", async (assert) => {
    class CustomComponent extends Component {}
    CustomComponent.template = xml`
        <div class="o_command_custom">
            <span t-esc="props.name"/>
        </div>
    `;

    testComponent = await mount(TestComponent, { env, target });
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    Component: CustomComponent,
                    name: "Command1",
                    action,
                },
                {
                    name: "Command2",
                    action,
                },
            ],
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2"]
    );
    assert.deepEqual(
        [...target.querySelectorAll(".o_command .o_command_default")].map((el) => el.textContent),
        ["Command2"]
    );
    assert.deepEqual(
        [...target.querySelectorAll(".o_command .o_command_custom")].map((el) => el.textContent),
        ["Command1"]
    );
});

QUnit.test("multi namespace with provider", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    name: "Command1",
                    action,
                },
                {
                    name: "Command2",
                    action,
                },
            ],
        },
        {
            namespace: "@",
            provide: () => [
                {
                    name: "Command3",
                    action,
                },
                {
                    name: "Command4",
                    action,
                },
            ],
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2"]
    );

    await editSearchBar("@");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command3", "Command4"]
    );
});

QUnit.test("apply a fuzzysearch on the namespace default not on the others", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    name: "Command1",
                    action,
                },
                {
                    name: "Command2",
                    action,
                },
            ],
        },
        {
            namespace: "@",
            provide: () => [
                {
                    name: "Command3",
                    action,
                },
                {
                    name: "Command4",
                    action,
                },
            ],
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2"]
    );
    await editSearchBar("c1");
    assert.containsN(target, ".o_command", 1);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1"]
    );

    await editSearchBar("@");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command3", "Command4"]
    );
    await editSearchBar("@c3");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command3", "Command4"]
    );
});

QUnit.test("multi provider with the same namespace", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    name: "Command1",
                    action,
                },
                {
                    name: "Command2",
                    action,
                },
            ],
        },
        {
            provide: () => [
                {
                    name: "Command3",
                    action,
                },
                {
                    name: "Command4",
                    action,
                },
            ],
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 4);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2", "Command3", "Command4"]
    );
});

QUnit.test("check the concurrency during a research", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const imSearchDef = makeDeferred();
    const provide = async (env, options) => {
        if (options.searchValue) {
            await imSearchDef;
        }
        return [
            {
                name: "a",
                action: () => {
                    assert.step("a");
                },
            },
            {
                name: "b",
                action: () => {
                    assert.step("b");
                },
            },
        ];
    };
    const providers = [{ namespace: "default", provide }];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 2);

    await editSearchBar("b");
    triggerHotkey("enter");
    await nextTick();
    assert.verifySteps([]);

    imSearchDef.resolve();
    await nextTick();
    assert.verifySteps(["b"]);
});

QUnit.test("open the command palette with a namespace already in the searchbar", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    name: "Command1",
                    action,
                },
                {
                    name: "Command2",
                    action,
                },
            ],
        },
        {
            namespace: "@",
            provide: () => [
                {
                    name: "Command3",
                    action,
                },
                {
                    name: "Command4",
                    action,
                },
            ],
        },
    ];
    const config = {
        namespace: "@",
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "@");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command3", "Command4"]
    );
});

QUnit.test("multi provider with categories", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const categoriesByNamespace = {
        default: ["cat1", "cat2"],
        "@": ["@cat1", "@cat2"],
    };
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    name: "Command1",
                    action,
                    category: "cat1",
                },
                {
                    name: "Command2",
                    action,
                    category: "cat2",
                },
                {
                    name: "Command3",
                    action,
                },
            ],
        },
        {
            namespace: "@",
            provide: () => [
                {
                    name: "Command4",
                    action,
                },
                {
                    name: "Command5",
                    action,
                    category: "@cat2",
                },
                {
                    name: "Command6",
                    action,
                    category: "@cat1",
                },
                {
                    name: "Command7",
                    action,
                    category: "@cat1",
                },
            ],
        },
    ];
    const config = {
        categoriesByNamespace,
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 3);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2", "Command3"]
    );
    assert.containsN(target, ".o_command_category", 3);
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(1) .o_command > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command1"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(2) .o_command > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command2"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(3) .o_command > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command3"]
    );

    await editSearchBar("@");
    await nextTick();
    assert.containsN(target, ".o_command", 4);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command6", "Command7", "Command5", "Command4"]
    );
    assert.containsN(target, ".o_command_category", 3);
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(1) .o_command > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command6", "Command7"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(2) .o_command > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command5"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(3) .o_command > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command4"]
    );
});

QUnit.test("don't display by categories if there is a search value", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const categoriesByNamespace = {
        default: ["cat1", "cat2"],
    };
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    name: "Command1",
                    action,
                    category: "cat1",
                },
                {
                    name: "Command2",
                    action,
                    category: "cat2",
                },
                {
                    name: "Command3",
                    action,
                },
            ],
        },
    ];
    const config = {
        categoriesByNamespace,
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 3);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2", "Command3"]
    );
    assert.containsN(target, ".o_command_category", 3);

    await editSearchBar("c");
    await nextTick();
    assert.containsN(target, ".o_command", 3);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2", "Command3"]
    );

    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(1) .o_command > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command1", "Command2", "Command3"]
    );
});

QUnit.test("click on command", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const commands = [
        {
            name: "Command1",
            action: () => {
                assert.step("C1");
            },
        },
        {
            name: "Command2",
            action: () => {
                assert.step("C2");
            },
        },
    ];
    const providers = [
        {
            provide: () => commands,
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2"]
    );
    let focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[0].name);
    await click(target, ".o_command.focused");
    assert.verifySteps(["C1"]);
});

QUnit.test("press enter on command", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const commands = [
        {
            name: "Command1",
            action: () => {
                assert.step("C1");
            },
        },
        {
            name: "Command2",
            action: () => {
                assert.step("C2");
            },
        },
    ];
    const providers = [
        {
            provide: () => commands,
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2"]
    );
    let focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[0].name);
    triggerHotkey("arrowdown");
    await nextTick();
    triggerHotkey("enter");
    await nextTick();

    assert.verifySteps(["C2"]);
});

QUnit.test("keyboard navigation scroll", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const commands = [
        { name: "Command1" },
        { name: "Command2" },
        { name: "Command3" },
        { name: "Command4" },
    ];
    const providers = [
        {
            provide: () => commands,
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });

    const isVisible = (el) => {
        // Returns the visibility of the element in the scrollable element
        return (
            el.getBoundingClientRect().bottom <=
                target.querySelector(".o_command_palette_listbox").getBoundingClientRect().bottom &&
            el.getBoundingClientRect().top >=
                target.querySelector(".o_command_palette_listbox").getBoundingClientRect().top
        );
    };

    const border = (el) => {
        // Returns the state of the element in relation to the borders
        const element = el.getBoundingClientRect();
        const scrollable = target
            .querySelector(".o_command_palette_listbox")
            .getBoundingClientRect();
        return {
            top: element.top === scrollable.top,
            bottom: element.bottom === scrollable.bottom,
        };
    };

    await nextTick();
    // The listbox height is set to be lower than the list of commands
    // to assure the command palette is scrollable. The palette is only able to
    // display three rows of commands so we are sure we always have one row
    // element out of bounds
    target.querySelectorAll(".o_command").forEach((e) => (e.style.height = "50px"));
    target.querySelector(".o_command_palette_listbox").style.maxHeight = "150px";
    target.querySelector(".o_command_category").style.padding = "0";
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 4);

    let focusedCommand = target.querySelector(".o_command.focused");
    assert.ok(
        isVisible(target.querySelector("#o_command_0")) &&
            isVisible(target.querySelector("#o_command_1")) &&
            isVisible(target.querySelector("#o_command_2")) &&
            !isVisible(target.querySelector("#o_command_3")),
        "commands 1-2-3 are visible"
    );
    assert.ok(
        border(focusedCommand).top && !border(focusedCommand).bottom,
        "the focus is at the top border"
    );

    triggerHotkey("arrowdown");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.ok(
        isVisible(target.querySelector("#o_command_0")) &&
            isVisible(target.querySelector("#o_command_1")) &&
            isVisible(target.querySelector("#o_command_2")) &&
            !isVisible(target.querySelector("#o_command_3")),
        "commands 1-2-3 are visible"
    );
    assert.ok(isVisible(target.querySelector("#o_command_1")), "the second element is visible");
    assert.ok(
        !border(focusedCommand).top && !border(focusedCommand).bottom,
        "the focus does not reach a border"
    );

    triggerHotkey("arrowdown");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.ok(
        isVisible(target.querySelector("#o_command_0")) &&
            isVisible(target.querySelector("#o_command_1")) &&
            isVisible(target.querySelector("#o_command_2")) &&
            !isVisible(target.querySelector("#o_command_3")),
        "commands 1-2-3 are visible"
    );
    assert.ok(
        !border(focusedCommand).top && border(focusedCommand).bottom,
        "the focus has reached the bottom border"
    );

    triggerHotkey("arrowdown");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.ok(
        !isVisible(target.querySelector("#o_command_0")) &&
            isVisible(target.querySelector("#o_command_1")) &&
            isVisible(target.querySelector("#o_command_2")) &&
            isVisible(target.querySelector("#o_command_3")),
        "commands 2-3-4 are visible"
    );
    assert.ok(
        !border(focusedCommand).top && border(focusedCommand).bottom,
        "the focus is still at the bottom border"
    );

    triggerHotkey("arrowup");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.ok(
        !isVisible(target.querySelector("#o_command_0")) &&
            isVisible(target.querySelector("#o_command_1")) &&
            isVisible(target.querySelector("#o_command_2")) &&
            isVisible(target.querySelector("#o_command_3")),
        "commands 2-3-4 are visible"
    );
    assert.ok(
        !border(focusedCommand).top && !border(focusedCommand).bottom,
        "the focus does not reach a border"
    );

    triggerHotkey("arrowup");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.ok(
        !isVisible(target.querySelector("#o_command_0")) &&
            isVisible(target.querySelector("#o_command_1")) &&
            isVisible(target.querySelector("#o_command_2")) &&
            isVisible(target.querySelector("#o_command_3")),
        "commands 2-3-4 are visible"
    );
    assert.ok(
        border(focusedCommand).top && !border(focusedCommand).bottom,
        "the focus has reached the top border"
    );

    triggerHotkey("arrowup");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.ok(
        isVisible(target.querySelector("#o_command_0")) &&
            isVisible(target.querySelector("#o_command_1")) &&
            isVisible(target.querySelector("#o_command_2")) &&
            !isVisible(target.querySelector("#o_command_3")),
        "commands 1-2-3 are visible"
    );
    assert.ok(
        border(focusedCommand).top && !border(focusedCommand).bottom,
        "the focus is still at the top border"
    );
});

QUnit.test("multi level command", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });
    const emptyMessageByNamespace = {
        default: "Empty Default",
    };
    const commands = [
        {
            name: "Command1",
            action: () => {
                return {
                    providers: [{ provide: () => [{ name: "Command lvl2", action: () => {} }] }],
                };
            },
        },
    ];
    const providers = [
        {
            provide: () => commands,
        },
    ];
    const config = {
        emptyMessageByNamespace,
        footerTemplate,
        placeholder: "placeholder test",
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    await editSearchBar("empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        "Empty Default"
    );
    assert.strictEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "placeholder test"
    );
    assert.containsOnce(target, ".o_command_palette_footer");
    assert.strictEqual(target.querySelector(".o_command_palette_footer").textContent, "My footer");

    await editSearchBar("");
    assert.containsN(target, ".o_command", 1);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1"]
    );
    let focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[0].name);
    triggerHotkey("enter");
    await nextTick();
    assert.containsN(target, ".o_command", 1);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command lvl2"]
    );

    // check that the configuration has been correctly cleaned
    await editSearchBar("empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        "No results found"
    );
    assert.strictEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "Search..."
    );
    assert.containsNone(target, ".o_command_palette_footer");
});

QUnit.test("command palette dialog can be rendered and closed on outside click", async (assert) => {
    testComponent = await mount(TestComponent, { env, target });

    const config = {
        providers: [],
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");

    // Close on outside click
    window.dispatchEvent(new MouseEvent("mousedown"));
    await nextTick();
    assert.containsNone(target, ".o_command_palette");
});

QUnit.test("navigate in the command palette with the arrows", async (assert) => {
    assert.expect(6);

    testComponent = await mount(TestComponent, { env, target });
    const action = () => {};
    const commands = [
        {
            name: "Command1",
            action,
        },
        {
            name: "Command2",
            action,
        },
        {
            name: "Command3",
            action,
        },
    ];
    const providers = [
        {
            provide: () => commands,
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();

    let focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[0].name);

    triggerHotkey("arrowdown");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[1].name);

    triggerHotkey("arrowdown");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[2].name);

    triggerHotkey("arrowdown");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[0].name);

    triggerHotkey("arrowup");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[2].name);

    triggerHotkey("arrowup");
    await nextTick();
    focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[1].name);
});

QUnit.test("navigate in the command palette with an empty list", async (assert) => {
    assert.expect(6);

    testComponent = await mount(TestComponent, { env, target });
    const providers = [
        {
            provide: () => [],
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");

    triggerHotkey("arrowdown");
    await nextTick();
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");

    triggerHotkey("arrowup");
    await nextTick();
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
});

QUnit.test("generate new session id when opened", async (assert) => {
    assert.expect(4);

    let lastSessionId;
    CommandPalette.lastSessionId = 0;
    testComponent = await mount(TestComponent, { env, target });
    const providers = [
        {
            provide: (env, {sessionId}) => {
                lastSessionId = sessionId;
                return [];
            },
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });

    await nextTick();
    assert.equal(lastSessionId, 0);

    await editSearchBar("a");
    assert.equal(lastSessionId, 0);

    window.dispatchEvent(new MouseEvent("mousedown"));
    await nextTick();
    assert.equal(lastSessionId, 0);

    env.services.dialog.add(CommandPaletteDialog, {
        config,
    });
    await nextTick();
    assert.equal(lastSessionId, 1);
});
