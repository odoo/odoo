/** @odoo-module **/

import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { browser } from "@web/core/browser/browser";
import { useCommand } from "@web/core/commands/command_hook";
import { commandService } from "@web/core/commands/command_service";
import { HotkeyCommandItem } from "@web/core/commands/default_providers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { uiService, useActiveElement } from "@web/core/ui/ui_service";
import testUtils from "@web/../tests/legacy/helpers/test_utils";
import { clearRegistryWithCleanup, makeTestEnv } from "../../helpers/mock_env";
import {
    click,
    destroy,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "../../helpers/utils";

import { Component, xml } from "@odoo/owl";

let env;
let target;
const serviceRegistry = registry.category("services");
const commandCategoryRegistry = registry.category("command_categories");
const commandProviderRegistry = registry.category("command_provider");

export async function editSearchBar(searchValue) {
    const searchBar = document.querySelector(".o_command_palette_search input");
    await testUtils.fields.editInput(searchBar, searchValue);
}

export async function backspaceSearchBar() {
    const searchBar = document.querySelector(".o_command_palette_search input");
    searchBar.dispatchEvent(new KeyboardEvent("keydown", { key: "backspace" }));
    await nextTick();
}

class TestComponent extends Component {
    get OverlayContainer() {
        return registry.category("main_components").get("OverlayContainer");
    }
}
TestComponent.template = xml`
  <div>
    <t t-component="OverlayContainer.Component" t-props="OverlayContainer.props" />
  </div>
`;

QUnit.module("Command Service", {
    async beforeEach() {
        const commandProviders = commandProviderRegistry
            .getEntries()
            .filter((provider) => ["command", "data-hotkeys"].includes(provider[0]));
        clearRegistryWithCleanup(commandProviderRegistry);
        commandProviders.forEach((provider) => {
            commandProviderRegistry.add(provider[0], provider[1]);
        });

        serviceRegistry
            .add("ui", uiService)
            .add("dialog", dialogService)
            .add("hotkey", hotkeyService)
            .add("localization", makeFakeLocalizationService())
            .add("command", commandService);

        commandCategoryRegistry.add("custom-nolabel", {}).add("custom", {}).add("default", {});

        patchWithCleanup(browser, {
            clearTimeout: () => {},
            setTimeout: (later, wait) => {
                later();
            },
        });

        env = await makeTestEnv();
        target = getFixture();
    },
});

QUnit.test("commands evilness 👹", async (assert) => {
    const command = env.services.command;
    function action() {}

    assert.throws(function () {
        command.add();
    }, /A Command must have a name and an action function/);
    assert.throws(function () {
        command.add(null);
    }, /A Command must have a name and an action function/);
    assert.throws(function () {
        command.add("");
    }, /A Command must have a name and an action function/);
    assert.throws(function () {
        command.add("", action);
    }, /A Command must have a name and an action function/);
    assert.throws(function () {
        command.add("command", null);
    }, /A Command must have a name and an action function/);
});

QUnit.test("useCommand hook", async (assert) => {
    assert.expect(5);

    class MyComponent extends TestComponent {
        setup() {
            useCommand("Take the throne", () => {
                assert.step("Hodor");
            });
        }
    }
    const comp = await mount(MyComponent, target, { env });

    triggerHotkey("control+k");
    await nextTick();
    assert.containsOnce(target, ".o_command");

    assert.deepEqual(target.querySelector(".o_command").textContent, "Take the throne");

    await click(target, ".o_command");
    assert.verifySteps(["Hodor"]);

    destroy(comp);
    triggerHotkey("control+k");
    await nextTick();
    assert.containsNone(target, ".o_command");
});

QUnit.test("useCommand hook when the activeElement change", async (assert) => {
    assert.expect(4);

    class MyComponent extends TestComponent {
        setup() {
            useCommand("Take the throne", () => {});
            useCommand("Lose the throne", () => {}, { global: true });
        }
    }

    class OtherComponent extends Component {
        setup() {
            useActiveElement("active");
            useCommand("I'm taking the throne", () => {});
        }
    }
    OtherComponent.template = xml`<div t-ref="active"></div>`;

    await mount(MyComponent, target, { env });
    triggerHotkey("control+k");
    await nextTick();
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((e) => e.textContent),
        ["Take the throne", "Lose the throne"]
    );
    triggerHotkey("escape");

    await mount(OtherComponent, target, { env });

    triggerHotkey("control+k");
    await nextTick();
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((e) => e.textContent),
        ["Lose the throne", "I'm taking the throne"]
    );
});

QUnit.test("useCommand hook with isAvailable", async (assert) => {
    let available = false;
    class MyComponent extends TestComponent {
        setup() {
            useCommand("Take the throne", () => {}, {
                isAvailable: () => {
                    return available;
                },
            });
        }
    }
    await mount(MyComponent, target, { env });

    triggerHotkey("control+k");
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");

    triggerHotkey("escape");
    await nextTick();
    available = true;
    triggerHotkey("control+k");
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsOnce(target, ".o_command");
});

QUnit.test("command with hotkey", async (assert) => {
    assert.expect(2);

    const hotkey = "a";
    env.services.command.add("test", () => assert.step(hotkey), {
        hotkey,
    });
    await nextTick();

    triggerHotkey("a");
    await nextTick();
    assert.verifySteps([hotkey]);
});

QUnit.test("global command with hotkey", async (assert) => {
    assert.expect(5);

    const globalHotkey = "a";
    env.services.command.add("testA", () => assert.step(globalHotkey), {
        global: true,
        hotkey: globalHotkey,
    });
    const hotkey = "b";
    env.services.command.add("testB", () => assert.step(hotkey), {
        hotkey,
    });
    await nextTick();

    triggerHotkey("a");
    await nextTick();
    triggerHotkey("b");
    await nextTick();
    assert.verifySteps([globalHotkey, hotkey]);

    class MyComponent extends Component {
        setup() {
            useActiveElement("active");
        }
    }
    MyComponent.template = xml`<div t-ref="active"><button/></div>`;
    await mount(MyComponent, target, { env });

    triggerHotkey("a");
    await nextTick();
    triggerHotkey("b");
    await nextTick();
    assert.verifySteps([globalHotkey]);
});

QUnit.test("command with hotkey and isAvailable", async (assert) => {
    assert.expect(3);

    const hotkey = "a";
    let isAvailable = false;
    env.services.command.add("test", () => assert.step(hotkey), {
        hotkey,
        isAvailable: () => isAvailable,
    });
    await nextTick();

    triggerHotkey("a");
    await nextTick();
    assert.verifySteps([]);

    isAvailable = true;
    triggerHotkey("a");
    await nextTick();
    assert.verifySteps([hotkey]);
});

QUnit.test("useCommand hook with hotkey and hotkeyOptions", async (assert) => {
    const allowRepeatKey = "a";
    const disallowRepeatKey = "b";
    const defaultBehaviourKey = "c";
    class MyComponent extends TestComponent {
        setup() {
            useCommand("Allow repeat key", () => assert.step(allowRepeatKey), {
                hotkey: allowRepeatKey,
                hotkeyOptions: {
                    allowRepeat: true,
                },
            });
            useCommand("Disallow repeat key", () => assert.step(disallowRepeatKey), {
                hotkey: disallowRepeatKey,
                hotkeyOptions: {
                    allowRepeat: false,
                },
            });
            useCommand("Default repeat key", () => assert.step(defaultBehaviourKey), {
                hotkey: defaultBehaviourKey,
            });
        }
    }
    await mount(MyComponent, target, { env });

    // Dispatch the three keys without repeat:
    triggerHotkey(allowRepeatKey);
    triggerHotkey(disallowRepeatKey);
    triggerHotkey(defaultBehaviourKey);
    await nextTick();

    assert.verifySteps([allowRepeatKey, disallowRepeatKey, defaultBehaviourKey]);

    // Dispatch the three keys with repeat:
    triggerHotkey(allowRepeatKey, false, { repeat: true });
    triggerHotkey(disallowRepeatKey, false, { repeat: true });
    triggerHotkey(defaultBehaviourKey, false, { repeat: true });
    await nextTick();

    assert.verifySteps([allowRepeatKey]);
});

QUnit.test("useCommand hook with hotkey and isAvailable", async (assert) => {
    const hotkeys = ["a", "b", "c", "d", "e"];
    class MyComponent extends TestComponent {
        setup() {
            useCommand("Command 1", () => assert.step(hotkeys[0]), {
                hotkey: hotkeys[0],
                isAvailable: () => true,
                hotkeyOptions: {
                    allowRepeat: true,
                    isAvailable: () => true,
                },
            });
            useCommand("Command 2", () => assert.step(hotkeys[1]), {
                hotkey: hotkeys[1],
                isAvailable: () => true,
                hotkeyOptions: {
                    allowRepeat: true,
                    isAvailable: () => false,
                },
            });
            useCommand("Command 3", () => assert.step(hotkeys[2]), {
                hotkey: hotkeys[2],
                isAvailable: () => false,
                hotkeyOptions: {
                    allowRepeat: true,
                    isAvailable: () => true,
                },
            });
            useCommand("Command 4", () => assert.step(hotkeys[3]), {
                hotkey: hotkeys[3],
                isAvailable: () => true,
                hotkeyOptions: {
                    allowRepeat: true,
                },
            });
            useCommand("Command 5", () => assert.step(hotkeys[4]), {
                hotkey: hotkeys[4],
                isAvailable: () => false,
                hotkeyOptions: {
                    allowRepeat: true,
                },
            });
        }
    }
    await mount(MyComponent, target, { env });

    for (const hotkey of hotkeys) {
        triggerHotkey(hotkey);
    }
    await nextTick();
    assert.verifySteps(["a", "d"]);

    triggerHotkey("control+k");
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 3);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command 1A", "Command 2B", "Command 4D"]
    );
});

QUnit.test("open command palette with command config", async (assert) => {
    const hotkey = "alt+a";
    const action = () => {};
    const provide = () => [
        {
            name: "Command1",
            action,
        },
    ];
    const providers = [{ provide }];
    env.services.command.add(
        "test",
        () => {
            return {
                providers,
            };
        },
        {
            hotkey,
        }
    );

    await mount(TestComponent, target, { env });

    triggerHotkey("alt+a");
    await nextTick();
    assert.containsN(target, ".o_command", 1);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command span:first-child")].map((el) => el.textContent),
        ["Command1"]
    );
});

QUnit.test("data-hotkey added to command palette", async (assert) => {
    assert.expect(8);

    class MyComponent extends Component {
        onClick() {
            assert.step("Hodor");
        }
    }
    MyComponent.components = { TestComponent };
    MyComponent.template = xml`
        <div>
            <button title="Aria Stark" data-hotkey="a" t-on-click="onClick" />
            <input title="Bran Stark" type="text" data-hotkey="b" />
            <button title="Sansa Stark" data-hotkey="c" style="display: none;" />
            <TestComponent />
        </div>
    `;
    await mount(MyComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command span:first-child")].map((el) => el.textContent),
        ["Aria stark", "Bran stark"]
    );

    // Click on first command
    await click(target, "#o_command_0");
    assert.containsNone(target, ".o_command_palette", "palette is closed due to command action");

    // Reopen palette
    triggerHotkey("control+k");
    await nextTick();

    // Click on second command
    assert.notStrictEqual(
        document.activeElement,
        target.querySelector("input[title='Bran Stark']"),
        "input should not have the focus"
    );
    await click(target, "#o_command_1");
    assert.containsNone(target, ".o_command_palette", "palette is closed due to command action");
    assert.strictEqual(
        document.activeElement,
        target.querySelector("input[title='Bran Stark']"),
        "input should now have the focus after matching command action has been executed"
    );

    // only step should come from the first command execution
    assert.verifySteps(["Hodor"]);
});

QUnit.test("access to hotkeys from the command palette", async (assert) => {
    assert.expect(9);

    const hotkey = "a";
    env.services.command.add("A", () => assert.step("A"), {
        hotkey,
    });

    class MyComponent extends Component {
        onClickB() {
            assert.step("B");
        }
        onClickC() {
            assert.step("C");
        }
    }
    MyComponent.components = { TestComponent };
    MyComponent.template = xml`
    <div>
      <button title="B" data-hotkey="b" t-on-click="onClickB" />
      <button title="C" data-hotkey="c" t-on-click="onClickC" />
      <TestComponent />
    </div>
  `;
    await mount(MyComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.containsN(target, ".o_command", 3);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command span:first-child")].map((el) => el.textContent),
        ["A", "B", "C"]
    );

    // Trigger the command a
    triggerHotkey("a");
    await nextTick();
    assert.containsNone(target, ".o_command_palette", "palette is closed due to command action");

    // Reopen palette
    triggerHotkey("control+k");
    await nextTick();

    // Trigger the command b
    triggerHotkey("b", true);
    await nextTick();
    assert.containsNone(target, ".o_command_palette", "palette is closed due to command action");

    // Reopen palette
    triggerHotkey("control+k");
    await nextTick();

    // Trigger the command c
    triggerHotkey("c", true);
    await nextTick();
    assert.containsNone(target, ".o_command_palette", "palette is closed due to command action");

    assert.verifySteps(["A", "B", "C"]);
});

QUnit.test("can be searched", async (assert) => {
    assert.expect(4);

    await mount(TestComponent, target, { env });

    // Register some commands
    function action() {}
    const names = ["Cersei Lannister", "Jaime Lannister", "Tyrion Lannister", "Tywin Lannister"];
    for (const name of names) {
        env.services.command.add(name, action);
    }
    await nextTick();

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").value,
        "",
        "search input is empty"
    );

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        names,
        "all commands are present"
    );

    // Search something
    await editSearchBar("jl");

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Jaime Lannister"],
        "only search matches are present"
    );

    // Clear search input
    await editSearchBar("");

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        names,
        "all commands are again present"
    );
});

QUnit.test("configure the empty message based on the namespace", async (assert) => {
    assert.expect(2);

    clearRegistryWithCleanup(commandProviderRegistry);

    commandProviderRegistry.add("default", {
        namespace: "default",
        provide: () => [],
    });

    commandProviderRegistry.add("@", {
        namespace: "@",
        provide: () => [],
    });

    const commandSetupRegistry = registry.category("command_setup");
    clearRegistryWithCleanup(commandSetupRegistry);
    commandSetupRegistry.add("default", {
        emptyMessage: "Empty Default",
    });
    commandSetupRegistry.add("@", {
        emptyMessage: "Empty @",
    });

    await mount(TestComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        "Empty Default"
    );

    await editSearchBar("@");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        "Empty @"
    );
});

QUnit.test("footer displays the right tips", async (assert) => {
    assert.expect(3);

    clearRegistryWithCleanup(commandProviderRegistry);

    commandProviderRegistry.add("default", {
        namespace: "default",
        provide: () => [],
    });

    commandProviderRegistry.add("@", {
        namespace: "@",
        provide: () => [],
    });

    commandProviderRegistry.add("!", {
        namespace: "!",
        provide: () => [],
    });

    commandProviderRegistry.add("#", {
        namespace: "#",
        provide: () => [],
    });

    const commandSetupRegistry = registry.category("command_setup");
    clearRegistryWithCleanup(commandSetupRegistry);
    commandSetupRegistry.add("default", {});
    commandSetupRegistry.add("@", {
        name: "FirstName",
    });

    await mount(TestComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();
    assert.strictEqual(
        target.querySelector(".o_command_palette_footer").textContent,
        "TIP — search for @FirstName"
    );

    // Close palette
    triggerHotkey("escape");
    commandSetupRegistry.add("!", {
        name: "SecondName",
    });
    // Open palette
    triggerHotkey("control+k");
    await nextTick();
    assert.strictEqual(
        target.querySelector(".o_command_palette_footer").textContent,
        "TIP — search for @FirstName and !SecondName"
    );
    // Close palette
    triggerHotkey("escape");
    commandSetupRegistry.add("#", {
        name: "ThirdName",
    });
    // Open palette
    triggerHotkey("control+k");
    await nextTick();
    assert.strictEqual(
        target.querySelector(".o_command_palette_footer").textContent,
        "TIP — search for @FirstName, !SecondName and #ThirdName"
    );
});

QUnit.test("namespaces display in the footer are still clickable", async (assert) => {
    const action = () => {};
    clearRegistryWithCleanup(commandProviderRegistry);
    commandProviderRegistry.add("@", {
        namespace: "@",
        provide: () => [
            {
                name: "Command@",
                action,
            },
        ],
    });
    commandProviderRegistry.add("#", {
        namespace: "#",
        provide: () => [
            {
                name: "Command#",
                action,
            },
        ],
    });

    const commandSetupRegistry = registry.category("command_setup");
    clearRegistryWithCleanup(commandSetupRegistry);
    commandSetupRegistry.add("default", {});
    commandSetupRegistry.add("@", {
        name: "users",
    });
    commandSetupRegistry.add("#", {
        name: "channels",
    });
    await mount(TestComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();
    assert.strictEqual(
        target.querySelector(".o_command_palette_footer").textContent,
        "TIP — search for @users and #channels"
    );
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        []
    );

    await click(target.querySelectorAll(".o_command_palette_footer .o_namespace")[0]);
    assert.strictEqual(
        target.querySelector(".o_command_palette_search .o_namespace").textContent,
        "@"
    );
    assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "");
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command@"]
    );

    await editSearchBar("Com");
    await click(target.querySelectorAll(".o_command_palette_footer .o_namespace")[1]);
    assert.strictEqual(
        target.querySelector(".o_command_palette_search .o_namespace").textContent,
        "#"
    );
    assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "Com");
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command#"]
    );

    await click(target.querySelectorAll(".o_command_palette_footer .o_namespace")[0]);
    assert.strictEqual(
        target.querySelector(".o_command_palette_search .o_namespace").textContent,
        "@"
    );
    assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "Com");
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command@"]
    );
});

QUnit.test("defined multiple providers with the same namespace", async (assert) => {
    assert.expect(2);

    clearRegistryWithCleanup(commandProviderRegistry);
    const action = () => {};

    const defaultNames = ["John", "Snow"];
    commandProviderRegistry.add("default", {
        namespace: "default",
        provide: () =>
            defaultNames.map((name) => ({
                action,
                name,
            })),
    });

    const otherNames = ["Cersei", "Lannister"];
    commandProviderRegistry.add("other", {
        provide: () =>
            otherNames.map((name) => ({
                action,
                name,
            })),
    });

    await mount(TestComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").value,
        "",
        "search input is empty"
    );

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        defaultNames.concat(otherNames),
        "all default commands are present"
    );
});

QUnit.test("can switch between command providers", async (assert) => {
    assert.expect(4);

    clearRegistryWithCleanup(commandProviderRegistry);
    const action = () => {};

    const defaultNames = ["John", "Snow"];
    commandProviderRegistry.add("default", {
        provide: () =>
            defaultNames.map((name) => ({
                action,
                name,
            })),
    });

    const otherNames = ["Cersei", "Lannister"];
    commandProviderRegistry.add("other", {
        namespace: "@",
        provide: () =>
            otherNames.map((name) => ({
                action,
                name,
            })),
    });

    await mount(TestComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").value,
        "",
        "search input is empty"
    );

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        defaultNames,
        "all default commands are present"
    );

    // Switch to the other provider
    await editSearchBar("@");

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        otherNames,
        "all other commands are present"
    );

    // Press backspace to recover the default provider
    await backspaceSearchBar();

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        defaultNames,
        "all default commands are again present"
    );
});

QUnit.test("multi level commands", async (assert) => {
    assert.expect(5);

    clearRegistryWithCleanup(commandProviderRegistry);
    const defaultNames = ["John", "Snow"];
    const otherNames = ["Cersei", "Lannister"];
    const configByNamespace = {
        default: {
            placeholder: "Who is the next King ?",
        },
    };
    const action = () => ({
        configByNamespace,
        providers: [
            {
                provide: () =>
                    otherNames.map((name) => ({
                        name,
                        action: () => {},
                    })),
            },
        ],
    });

    commandProviderRegistry.add("default", {
        provide: () =>
            defaultNames.map((name) => ({
                action,
                name,
            })),
    });

    await mount(TestComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").value,
        "",
        "search input is empty"
    );

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "Search for a command...",
        "the default placeholder is correctly displayed"
    );

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        defaultNames,
        "all default commands are present"
    );

    await click(target, ".o_command.focused");
    await nextTick();

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "Who is the next King ?",
        "the new placeholder is correctly displayed"
    );

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        otherNames,
        "all default commands are present"
    );
});

QUnit.test("multi level commands with hotkey", async (assert) => {
    assert.expect(5);

    clearRegistryWithCleanup(commandProviderRegistry);

    const otherNames = ["Cersei", "Lannister"];
    const configByNamespace = {
        default: {
            placeholder: "Who is the next King ?",
        },
    };
    const action = () => ({
        configByNamespace,
        providers: [
            {
                provide: () =>
                    otherNames.map((name) => ({
                        name,
                        action: () => {},
                    })),
            },
        ],
    });

    const hotkey = "a";
    const name = "John";
    commandProviderRegistry.add("default", {
        provide: () => [
            {
                Component: HotkeyCommandItem,
                action,
                name,
                props: {
                    hotkey,
                },
            },
        ],
    });

    await mount(TestComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").value,
        "",
        "search input is empty"
    );

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "Search for a command...",
        "the default placeholder is correctly displayed"
    );

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent.toLowerCase()),
        [(name + hotkey).toLowerCase()],
        "all default commands are present"
    );

    triggerHotkey("a");
    await nextTick();

    assert.deepEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "Who is the next King ?",
        "the new placeholder is correctly displayed"
    );

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        otherNames,
        "all default commands are present"
    );
});

QUnit.test("command categories", async (assert) => {
    await mount(TestComponent, target, { env });

    // Register some commands
    function action() {}
    env.services.command.add("a", action, { category: "custom-nolabel" });
    env.services.command.add("b", action, { category: "custom" });
    env.services.command.add("c", action);
    env.services.command.add("d", action, { category: "invalid-category" });
    await nextTick();

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.containsN(target, ".o_command_category", 3);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command_category")].map((el) => el.textContent),
        ["a", "b", "cd"]
    );
});

QUnit.test("data-command-category", async (assert) => {
    assert.expect(3);

    class MyComponent extends Component {}
    MyComponent.components = { TestComponent };
    MyComponent.template = xml`
    <div>
      <div>
        <button title="Aria Stark" data-hotkey="a" />
        <button title="Bran Stark" data-hotkey="b" />
      </div>
      <div data-command-category="custom">
        <button title="Robert Baratheon" data-hotkey="r" />
        <button title="Joffrey Baratheon" data-hotkey="j" />
      </div>
      <TestComponent />
    </div>
  `;
    await mount(MyComponent, target, { env });

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.containsN(target, ".o_command", 4);
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Robert baratheon", "Joffrey baratheon"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(2) .o_command > a > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Aria stark", "Bran stark"]
    );
});

QUnit.test("display shortcuts correctly for non-MacOS ", async (assert) => {
    class MyComponent extends Component {}
    MyComponent.components = { TestComponent };
    MyComponent.template = xml`
    <div>
      <button title="Click" data-hotkey="f" />
      <TestComponent />
    </div>
  `;

    await mount(MyComponent, target, { env });

    // Register some commands
    function action() {}
    env.services.command.add("a", action);
    env.services.command.add("b", action, { hotkey: "alt+b" });
    env.services.command.add("c", action, { hotkey: "c" });
    env.services.command.add("d", action, {
        hotkey: "control+d",
    });
    env.services.command.add("e", action, {
        hotkey: "alt+control+e",
    });
    await nextTick();

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["a", "bALT + B", "cC", "dCONTROL + D", "eALT + CONTROL + E", "ClickALT + F"]
    );
});

QUnit.test("display shortcuts correctly for MacOS ", async (assert) => {
    patchWithCleanup(browser, {
        navigator: {
            userAgent: browser.navigator.userAgent.replace(/\([^)]*\)/, "(MacOs)"),
        },
    });

    class MyComponent extends Component {}
    MyComponent.components = { TestComponent };
    MyComponent.template = xml`
        <div>
        <button title="Click" data-hotkey="f" />
        <TestComponent />
        </div>
    `;

    await mount(MyComponent, target, { env });

    // Register some commands
    function action() {}
    env.services.command.add("a", action);
    env.services.command.add("b", action, { hotkey: "alt+b" });
    env.services.command.add("c", action, { hotkey: "c" });
    env.services.command.add("d", action, {
        hotkey: "control+d",
    });
    env.services.command.add("e", action, {
        hotkey: "alt+control+e",
    });
    await nextTick();

    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["a", "bCONTROL + B", "cC", "dCOMMAND + D", "eCONTROL + COMMAND + E", "ClickCONTROL + F"]
    );
});

QUnit.test(
    "display shortcuts correctly for non-MacOS with a new overlayModifier",
    async (assert) => {
        const hotkeyService = serviceRegistry.get("hotkey");
        patchWithCleanup(hotkeyService, {
            overlayModifier: "alt+control",
        });

        class MyComponent extends Component {}
        MyComponent.components = { TestComponent };
        MyComponent.template = xml`
    <div>
      <button title="Click" data-hotkey="a" />
      <TestComponent />
    </div>
  `;

        await mount(MyComponent, target, { env });
        // Open palette
        triggerHotkey("control+k");
        await nextTick();

        assert.deepEqual(
            [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
            ["ClickALT + CONTROL + A"]
        );
    }
);

QUnit.test("display shortcuts correctly for MacOS with a new overlayModifier", async (assert) => {
    patchWithCleanup(browser, {
        navigator: {
            userAgent: browser.navigator.userAgent.replace(/\([^)]*\)/, "(MacOs)"),
        },
    });

    const hotkeyService = serviceRegistry.get("hotkey");
    patchWithCleanup(hotkeyService, {
        overlayModifier: "alt+control",
    });

    class MyComponent extends Component {}
    MyComponent.components = { TestComponent };
    MyComponent.template = xml`
    <div>
      <button title="Click" data-hotkey="a" />
      <TestComponent />
    </div>
  `;

    await mount(MyComponent, target, { env });
    // Open palette
    triggerHotkey("control+k");
    await nextTick();

    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["ClickCONTROL + COMMAND + A"]
    );
});

QUnit.test("openMainPalette with onClose", async (assert) => {
    const command = env.services.command;
    command.openMainPalette({}, () => {
        assert.step("onClose");
    });
    await mount(TestComponent, target, { env });

    await nextTick();
    assert.containsOnce(target, ".o_command_palette");

    triggerHotkey("escape");
    await nextTick();
    assert.verifySteps(["onClose"]);
});

QUnit.test("uses openPalette to modify the config used by the command palette", async (assert) => {
    const action = () => {};
    env.services.command.add("Command1", action);

    await mount(TestComponent, target, { env });

    triggerHotkey("control+k");
    await nextTick();
    assert.deepEqual(target.querySelector(".o_command_palette_search input").value, "");
    assert.containsN(target, ".o_command", 1);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command span:first-child")].map((el) => el.textContent),
        ["Command1"]
    );

    const provide = () => [
        {
            name: "Command2",
            action,
        },
    ];
    const providers = [{ provide }];
    const configCustom = {
        searchValue: "Command",
        providers,
    };
    env.services.command.openPalette(configCustom);
    await nextTick();
    assert.containsN(target, ".o_command", 1);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command span:first-child")].map((el) => el.textContent),
        ["Command2"]
    );
    assert.deepEqual(target.querySelector(".o_command_palette_search input").value, "Command");
});

QUnit.test(
    "ensure that calling openPalette multiple times successfully loads the last config for the command palette",
    async (assert) => {
        const providePromise1 = makeDeferred();
        const providePromise2 = makeDeferred();
        const action = () => {};

        await mount(TestComponent, target, { env });

        const provide = [
            async () => {
                await providePromise1;
                return [
                    {
                        name: "Command1",
                        action,
                    },
                ];
            },
            async () => {
                await providePromise2;
                return [
                    {
                        name: "Command2",
                        action,
                    },
                ];
            },
        ];
        const configCustom1 = {
            searchValue: "Command",
            providers: [{ provide: provide[0] }],
        };
        const configCustom2 = {
            searchValue: "Command",
            providers: [{ provide: provide[1] }],
        };

        env.services.command.openPalette(configCustom1);
        await nextTick();
        assert.containsNone(target, ".o_command_palette");
        env.services.command.openPalette(configCustom2);
        await nextTick();
        assert.containsNone(target, ".o_command_palette");
        providePromise1.resolve();
        await nextTick();
        // First config should not be loaded since a second config was sent.
        assert.containsNone(target, ".o_command_palette");
        providePromise2.resolve();
        await nextTick();
        // Second config should be loaded properly.
        assert.containsN(target, ".o_command", 1);
        assert.deepEqual(
            [...target.querySelectorAll(".o_command span:first-child")].map((el) => el.textContent),
            ["Command2"]
        );
        assert.deepEqual(target.querySelector(".o_command_palette_search input").value, "Command");
    }
);
