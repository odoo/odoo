/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CommandPalette } from "@web/core/commands/command_palette";
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
    mount,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "../../helpers/utils";
import { backspaceSearchBar, editSearchBar } from "./command_service_tests";

import { Component, xml } from "@odoo/owl";

let env;
let target;
const serviceRegistry = registry.category("services");

class FooterComponent extends Component {}
FooterComponent.template = xml`<span>My footer</span>`;

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

QUnit.module("Command Palette", {
    async beforeEach() {
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("command", commandService);

        patchWithCleanup(browser, {
            clearTimeout: () => {},
            setTimeout: (later) => {
                later();
            },
        });

        env = await makeTestEnv();
        target = getFixture();
    },
});

QUnit.test("empty providers", async (assert) => {
    await mount(TestComponent, target, { env });
    const config = {
        providers: [],
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        "No result found"
    );
    assert.strictEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "Search..."
    );
    assert.containsNone(target, ".o_command_palette_footer");
});

QUnit.test("custom empty message", async (assert) => {
    await mount(TestComponent, target, { env });
    const configByNamespace = {
        default: {
            emptyMessage: "Empty Default",
        },
        "@": {
            emptyMessage: "Empty @",
        },
        "#": {
            emptyMessage: "Empty #",
        },
    };
    const provide = () => [];
    const providers = [
        { namespace: "@", provide },
        { namespace: "#", provide },
    ];
    const config = {
        configByNamespace,
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        configByNamespace["default"].emptyMessage
    );

    await editSearchBar("@");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        configByNamespace["@"].emptyMessage
    );

    await editSearchBar("#");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_listbox_empty").textContent,
        configByNamespace["#"].emptyMessage
    );
});

QUnit.test("custom debounce delay", async (assert) => {
    patchWithCleanup(browser, {
        clearTimeout: () => {},
        setTimeout: (later, delay) => {
            assert.step(delay.toString());
            later();
        },
    });

    await mount(TestComponent, target, { env });
    const configByNamespace = {
        "@": {
            debounceDelay: 200,
        },
        "#": {
            debounceDelay: 100,
        },
    };
    const action = () => {};
    const provide = () => [
        {
            name: "Command1",
            action,
        },
        {
            name: "Command2",
            action,
        },
    ];
    const providers = [
        { namespace: "@", provide },
        { namespace: "#", provide },
    ];
    const config = {
        configByNamespace,
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    await editSearchBar("com");
    await editSearchBar("@");
    await editSearchBar("#");
    await backspaceSearchBar();
    assert.verifySteps(["0", "200", "100", "0"]);
});

QUnit.test("concurrency with custom debounce delay", async (assert) => {
    const def = makeDeferred();
    patchWithCleanup(browser, {
        clearTimeout: () => {},
        setTimeout: async (later, delay) => {
            if (delay === 200) {
                await def;
            }
            later();
        },
    });

    await mount(TestComponent, target, { env });
    const configByNamespace = {
        "@": {
            debounceDelay: 200,
        },
        "#": {
            debounceDelay: 100,
        },
    };
    const action = () => {};
    const providers = [
        {
            namespace: "@",
            provide: () => [
                {
                    name: "Command@",
                    action,
                },
            ],
        },
        {
            namespace: "#",
            provide: () => [
                {
                    name: "Command#",
                    action,
                },
            ],
        },
    ];
    const config = {
        configByNamespace,
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    assert.containsNone(target, ".o_command_palette .o_namespace");

    await editSearchBar("@");
    await nextTick();
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        []
    );

    await editSearchBar("#");
    await nextTick();
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "#");
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command#"]
    );

    def.resolve();
    await nextTick();
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "#");
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command#"]
    );
});

QUnit.test("custom placeholder", async (assert) => {
    await mount(TestComponent, target, { env });
    const configByNamespace = {
        default: {
            placeholder: "default placeholder",
        },
        "@": {
            placeholder: "@ placeholder",
        },
    };
    const config = {
        configByNamespace,
        providers: [
            {
                namespace: "@",
                provide: () => [],
            },
        ],
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command");
    assert.containsOnce(target, ".o_command_palette_listbox_empty");
    assert.strictEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "default placeholder"
    );

    await editSearchBar("@");
    assert.strictEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "@ placeholder"
    );
});

QUnit.test("add a footer", async (assert) => {
    await mount(TestComponent, target, { env });
    const config = {
        providers: [],
        FooterComponent,
    };
    env.services.dialog.add(CommandPalette, {
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

    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
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
    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command_palette .o_namespace");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2"]
    );

    await editSearchBar("@");
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command3", "Command4"]
    );
});

QUnit.test("apply a fuzzysearch on the namespace default not on the others", async (assert) => {
    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
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
    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
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
    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
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

QUnit.test(
    "open the command palette with a searchValue already in the searchbar",
    async (assert) => {
        await mount(TestComponent, target, { env });
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
            searchValue: "C1",
            providers,
        };
        env.services.dialog.add(CommandPalette, {
            config,
        });
        await nextTick();
        assert.containsOnce(target, ".o_command_palette");
        assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "C1");
        assert.containsN(target, ".o_command", 1);
        assert.deepEqual(
            [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
            ["Command1"]
        );
    }
);

QUnit.test("open the command palette with a namespace already in the searchbar", async (assert) => {
    await mount(TestComponent, target, { env });
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
        searchValue: "@",
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command3", "Command4"]
    );
});

QUnit.test("open the command palette with a searchValue with a namespace", async (assert) => {
    await mount(TestComponent, target, { env });
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
        searchValue: "@Test",
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");
    assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "Test");
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command3", "Command4"]
    );
});

QUnit.test("open the command palette with a searchValue without namespace", async (assert) => {
    await mount(TestComponent, target, { env });
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
        searchValue: "Command1",
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsNone(target, ".o_command_palette .o_namespace");
    assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "Command1");
    assert.containsN(target, ".o_command", 1);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1"]
    );
});

QUnit.test("multi provider with categories", async (assert) => {
    await mount(TestComponent, target, { env });
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
    const configByNamespace = {
        default: {
            categories: ["cat1", "cat2"],
        },
        "@": {
            categories: ["@cat1", "@cat2"],
        },
    };
    const config = {
        configByNamespace,
        providers,
    };
    env.services.dialog.add(CommandPalette, {
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
                ".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command1"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(2) .o_command > a > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command2"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(3) .o_command > a > div > span:first-child"
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
                ".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command6", "Command7"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(2) .o_command > a > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command5"]
    );
    assert.deepEqual(
        [
            ...target.querySelectorAll(
                ".o_command_category:nth-of-type(3) .o_command > a > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command4"]
    );
});

QUnit.test("don't display by categories if there is a search value", async (assert) => {
    await mount(TestComponent, target, { env });
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
    const configByNamespace = {
        default: {
            categories: ["cat1", "cat2"],
        },
    };
    const config = {
        configByNamespace,
        providers,
    };
    env.services.dialog.add(CommandPalette, {
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
                ".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child"
            ),
        ].map((el) => el.textContent),
        ["Command1", "Command2", "Command3"]
    );
});

QUnit.test("click on command", async (assert) => {
    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2"]
    );
    const focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[0].name);
    await click(target, ".o_command.focused");
    assert.verifySteps(["C1"]);
});

QUnit.test("press enter on command", async (assert) => {
    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Command1", "Command2"]
    );
    const focusedCommand = target.querySelector(".o_command.focused");
    assert.strictEqual(focusedCommand.textContent, commands[0].name);
    triggerHotkey("arrowdown");
    await nextTick();
    triggerHotkey("enter");
    await nextTick();

    assert.verifySteps(["C2"]);
});

QUnit.test("keyboard navigation scroll", async (assert) => {
    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
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
    await mount(TestComponent, target, { env });
    const configByNamespace = {
        default: {
            emptyMessage: "Empty Default",
            placeholder: "placeholder test",
        },
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
        configByNamespace,
        FooterComponent,
        providers,
    };
    env.services.dialog.add(CommandPalette, {
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
    const focusedCommand = target.querySelector(".o_command.focused");
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
        "No result found"
    );
    assert.strictEqual(
        target.querySelector(".o_command_palette_search input").placeholder,
        "Search..."
    );
    assert.containsNone(target, ".o_command_palette_footer");
});

QUnit.test("command palette dialog can be rendered and closed on outside click", async (assert) => {
    await mount(TestComponent, target, { env });

    const config = {
        providers: [],
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");

    // Close on outside click
    document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    await nextTick();
    assert.containsNone(target, ".o_command_palette");
});

QUnit.test("navigate in the command palette with the arrows", async (assert) => {
    assert.expect(6);

    await mount(TestComponent, target, { env });
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
    env.services.dialog.add(CommandPalette, {
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

    await mount(TestComponent, target, { env });
    const providers = [
        {
            provide: () => [],
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPalette, {
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

QUnit.test("bold the searchValue on the commands", async (assert) => {
    await mount(TestComponent, target, { env });
    const action = () => {};
    const providers = [
        {
            namespace: "@",
            provide: () => [
                {
                    name: "Test",
                    action,
                },
                {
                    name: "test hello",
                    action,
                },
                {
                    name: "hello test",
                    action,
                },
                {
                    name: "hello Test hello",
                    action,
                },
                {
                    name: "TeSt hello Test hello TEST",
                    action,
                },
            ],
        },
    ];
    const config = {
        searchValue: "@",
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 5);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command b")].map((el) => el.textContent),
        []
    );

    await editSearchBar("@test");
    assert.containsN(target, ".o_command", 5);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((command) => {
            return [...command.querySelectorAll(".o_command_name b")].map((el) => el.textContent);
        }),
        [["Test"], ["test"], ["test"], ["Test"], ["TeSt", "Test", "TEST"]]
    );
});

QUnit.test("bold the searchValue on the commands with special char", async (assert) => {
    await mount(TestComponent, target, { env });
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    name: "Test&",
                    action,
                },
            ],
        },
    ];
    const config = {
        searchValue: "&",
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 1);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
        ["Test&"]
    );
    assert.deepEqual(
        [...target.querySelectorAll(".o_command b")].map((el) => el.textContent),
        ["&"]
    );
});

QUnit.test("remove namespace with backspace", async (assert) => {
    await mount(TestComponent, target, { env });
    const provide = () => [];
    const providers = [
        {
            provide,
        },
        {
            namespace: "@",
            provide,
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    await editSearchBar("@");
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");

    // remove namespace "@" because the input is empty
    await backspaceSearchBar();
    assert.containsNone(target, ".o_command_palette .o_namespace");
    assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "");

    await editSearchBar("@NotEmpty");
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");
    assert.strictEqual(target.querySelector(".o_command_palette_search input").value, "NotEmpty");

    // Do not remove the namespace "@" because the input is not empty
    await backspaceSearchBar();
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");

    await editSearchBar("@");
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");

    // Does not remove the namespace if the backspace is repeatedly applied.
    // You don't want to remove the namespace by pressing the "backspace" key
    const searchBar = document.querySelector(".o_command_palette_search input");
    searchBar.dispatchEvent(new KeyboardEvent("keydown", { key: "backspace", repeat: true }));
    await nextTick();
    assert.strictEqual(target.querySelector(".o_command_palette .o_namespace").innerText, "@");
});

QUnit.test("generate new session id when opened", async (assert) => {
    assert.expect(4);

    let lastSessionId;
    CommandPalette.lastSessionId = 0;
    mount(TestComponent, target, { env });
    const providers = [
        {
            provide: (env, { sessionId }) => {
                lastSessionId = sessionId;
                return [];
            },
        },
    ];
    const config = {
        providers,
    };
    env.services.dialog.add(CommandPalette, {
        config,
    });

    await nextTick();
    assert.equal(lastSessionId, 0);

    await editSearchBar("a");
    assert.equal(lastSessionId, 0);

    document.body.dispatchEvent(new MouseEvent("mousedown"));
    await nextTick();
    assert.equal(lastSessionId, 0);

    env.services.dialog.add(CommandPalette, {
        config,
    });
    await nextTick();
    assert.equal(lastSessionId, 1);
});

QUnit.test("checks that href is correctly used", async (assert) => {
    await mount(TestComponent, target, { env });
    const providers = [
        {
            namespace: "@",
            provide: () => [
                {
                    name: "Command with link",
                    action: () => {
                        assert.step("command_with_link_clicked");
                    },
                    href: "https://www.odoo.com",
                },
                {
                    name: "Command without link",
                    action: () => {},
                },
            ],
        },
    ];
    const config = { providers };
    env.services.dialog.add(CommandPalette, {
        config,
    });
    patchWithCleanup(window, {
        open: (href) => {
            assert.step(href.toString());
        },
    });
    await nextTick();
    await editSearchBar("@");
    const command = target.querySelector(".o_command_palette .o_command");
    // Check that command has link inside it
    assert.strictEqual(command.querySelector("a").getAttribute("href"), "https://www.odoo.com");
    // Check that we get url when doing ctrl+enter on a command having a link inside it
    triggerHotkey("control+enter");
    await nextTick();
    assert.verifySteps(["https://www.odoo.com"]);
    // Check that command has no link inside it
    const commandWithoutLink = target.querySelector(".o_command_palette .o_command:nth-child(2)");
    assert.strictEqual(commandWithoutLink.querySelector("a").getAttribute("href"), null);
    // Check that clicking on a command having a link inside it triggers the command action
    // instead of redirecting to the href (last step because it closes the command palette).
    await click(command);
    await nextTick();
    assert.verifySteps(["command_with_link_clicked"]);
});
