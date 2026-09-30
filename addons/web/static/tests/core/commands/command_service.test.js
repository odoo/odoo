import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { keyDown, press, queryAllTexts } from "@odoo/hoot-dom";
import {
    Deferred,
    advanceFrame,
    advanceTime,
    animationFrame,
    mockUserAgent,
} from "@odoo/hoot-mock";
import {
    contains,
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { Component, reactive, xml } from "@odoo/owl";

import { useCommand } from "@web/core/commands/command_hook";
import { HotkeyCommandItem } from "@web/core/commands/default_providers";
import { registry } from "@web/core/registry";
import { useActiveElement } from "@web/core/ui/ui_service";

class TestComponent extends Component {
    static template = xml`<div />`;
    static props = ["*"];
}

class Parent extends Component {
    static template = xml`
      <t t-component="props.componentInfo.Component" t-if="props.componentInfo.Component" />
    `;
    static props = ["*"];
}

const commandProviderRegistry = registry.category("command_provider");
const commandSetupRegistry = registry.category("command_setup");

describe.current.tags("desktop");

beforeEach(async () => {
    commandProviderRegistry.getEntries().forEach(([key]) => {
        if (!["command", "data-hotkeys", "default"].includes(key)) {
            commandProviderRegistry.remove(key);
        }
    });
    commandSetupRegistry.getEntries().forEach(([key]) => {
        if (!["command", "data-hotkeys", "default"].includes(key)) {
            commandSetupRegistry.remove(key);
        }
    });
    await makeMockEnv();
    const commandCategoryRegistry = registry.category("command_categories");
    // Adding default last. The order of insertion of categories matters
    commandCategoryRegistry.remove("default");
    commandCategoryRegistry.add("custom-nolabel", {}).add("custom", {}).add("default", {});
});

test("commands evilness 👹", async () => {
    expect(function () {
        getService("command").add();
    }).toThrow(/A Command must have a name and an action function/);
    expect(function () {
        getService("command").add(null);
    }).toThrow(/A Command must have a name and an action function/);
    expect(function () {
        getService("command").add("");
    }).toThrow(/A Command must have a name and an action function/);
    expect(function () {
        getService("command").add("", function action() {});
    }).toThrow(/A Command must have a name and an action function/);
    expect(function () {
        getService("command").add("command", null);
    }).toThrow(/A Command must have a name and an action function/);
});

test("useCommand hook", async () => {
    class MyComponent extends TestComponent {
        setup() {
            useCommand("Take the throne", () => {
                expect.step("Hodor");
            });
        }
    }
    const componentInfo = reactive({ Component: MyComponent });
    await mountWithCleanup(Parent, { props: { componentInfo } });

    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command").toHaveCount(1);
    expect(".o_command").toHaveText("Take the throne");

    await contains(".o_command").click();
    expect.verifySteps(["Hodor"]);

    componentInfo.Component = null;
    await animationFrame();

    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command").toHaveCount(0);
});

test("useCommand hook when the activeElement change", async () => {
    class MyComponent extends TestComponent {
        setup() {
            useCommand("Take the throne", () => {});
            useCommand("Lose the throne", () => {}, { global: true });
        }
    }

    class OtherComponent extends Component {
        static template = xml`<div t-ref="active"><div tabindex="1">visible</div></div>`;
        static props = ["*"];
        setup() {
            useActiveElement("active");
            useCommand("I'm taking the throne", () => {});
        }
    }

    await mountWithCleanup(MyComponent);
    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Take the throne", "Lose the throne"]);
    await press("escape");
    await animationFrame();

    await mountWithCleanup(OtherComponent, { noMainContainer: true });
    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Lose the throne", "I'm taking the throne"]);
});

test("useCommand hook with isAvailable", async () => {
    let available = false;
    class MyComponent extends TestComponent {
        setup() {
            useCommand("Take the throne", () => {}, {
                isAvailable: () => available,
            });
        }
    }
    await mountWithCleanup(MyComponent);

    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);

    await press("escape");
    await animationFrame();
    available = true;
    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(1);
});

test("command with hotkey", async () => {
    const hotkey = "a";
    getService("command").add("test", () => expect.step(hotkey), {
        hotkey,
    });
    await animationFrame();

    await press("a");
    expect.verifySteps([hotkey]);
});

test("global command with hotkey", async () => {
    const globalHotkey = "a";
    getService("command").add("testA", () => expect.step(globalHotkey), {
        global: true,
        hotkey: globalHotkey,
    });
    const hotkey = "b";
    getService("command").add("testB", () => expect.step(hotkey), {
        hotkey,
    });
    await animationFrame();

    await press("a");
    expect.verifySteps([globalHotkey]);
    await press("b");
    expect.verifySteps([hotkey]);

    class MyComponent extends Component {
        static template = xml`<div t-ref="active"><button>visible</button></div>`;
        static props = ["*"];
        setup() {
            useActiveElement("active");
        }
    }
    await mountWithCleanup(MyComponent);

    await press("a");
    await press("b");
    expect.verifySteps([globalHotkey]);
});

test("command with hotkey and isAvailable", async () => {
    const hotkey = "a";
    let isAvailable = false;
    getService("command").add("test", () => expect.step(hotkey), {
        hotkey,
        isAvailable: () => isAvailable,
    });

    await press("a");
    await animationFrame();
    expect.verifySteps([]);

    isAvailable = true;
    await press("a");
    await animationFrame();
    expect.verifySteps([hotkey]);
});

test("useCommand hook with hotkey and hotkeyOptions", async () => {
    const allowRepeatKey = "a";
    const disallowRepeatKey = "b";
    const defaultBehaviourKey = "c";
    class MyComponent extends TestComponent {
        setup() {
            useCommand("Allow repeat key", () => expect.step(allowRepeatKey), {
                hotkey: allowRepeatKey,
                hotkeyOptions: {
                    allowRepeat: true,
                },
            });
            useCommand("Disallow repeat key", () => expect.step(disallowRepeatKey), {
                hotkey: disallowRepeatKey,
                hotkeyOptions: {
                    allowRepeat: false,
                },
            });
            useCommand("Default repeat key", () => expect.step(defaultBehaviourKey), {
                hotkey: defaultBehaviourKey,
            });
        }
    }
    await mountWithCleanup(MyComponent);

    await keyDown(allowRepeatKey);
    await keyDown(allowRepeatKey);
    await animationFrame();

    expect.verifySteps([allowRepeatKey, allowRepeatKey]);

    await keyDown(disallowRepeatKey);
    await keyDown(disallowRepeatKey);
    await animationFrame();

    expect.verifySteps([disallowRepeatKey]);

    await keyDown(defaultBehaviourKey);
    await keyDown(defaultBehaviourKey);
    await animationFrame();

    expect.verifySteps([defaultBehaviourKey]);
});

test("useCommand hook with hotkey and isAvailable", async () => {
    const hotkeys = ["a", "b", "c", "d", "e"];
    class MyComponent extends TestComponent {
        setup() {
            useCommand("Command 1", () => expect.step(hotkeys[0]), {
                hotkey: hotkeys[0],
                isAvailable: () => true,
                hotkeyOptions: {
                    allowRepeat: true,
                    isAvailable: () => true,
                },
            });
            useCommand("Command 2", () => expect.step(hotkeys[1]), {
                hotkey: hotkeys[1],
                isAvailable: () => true,
                hotkeyOptions: {
                    allowRepeat: true,
                    isAvailable: () => false,
                },
            });
            useCommand("Command 3", () => expect.step(hotkeys[2]), {
                hotkey: hotkeys[2],
                isAvailable: () => false,
                hotkeyOptions: {
                    allowRepeat: true,
                    isAvailable: () => true,
                },
            });
            useCommand("Command 4", () => expect.step(hotkeys[3]), {
                hotkey: hotkeys[3],
                isAvailable: () => true,
                hotkeyOptions: {
                    allowRepeat: true,
                },
            });
            useCommand("Command 5", () => expect.step(hotkeys[4]), {
                hotkey: hotkeys[4],
                isAvailable: () => false,
                hotkeyOptions: {
                    allowRepeat: true,
                },
            });
        }
    }
    await mountWithCleanup(MyComponent);

    for (const hotkey of hotkeys) {
        await press(hotkey);
    }
    await animationFrame();
    expect.verifySteps(["a", "d"]);

    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(3);
    expect(queryAllTexts(".o_command")).toEqual(["Command 1\nA", "Command 2\nB", "Command 4\nD"]);
});

test("open command palette with command config", async () => {
    const hotkey = "alt+a";
    const action = () => {};
    const provide = () => [
        {
            name: "Command1",
            action,
        },
    ];
    const providers = [{ provide }];
    getService("command").add(
        "test",
        () => ({
            providers,
        }),
        {
            hotkey,
        }
    );

    await mountWithCleanup(TestComponent);

    await press(["alt", "a"]);
    await animationFrame();
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command span:first-child")).toEqual(["Command1"]);
});

test("data-hotkey added to command palette", async () => {
    class MyComponent extends Component {
        static components = { TestComponent };
        static template = xml`
            <div>
                <button title="Aria Stark" data-hotkey="a" t-on-click="onClick">visible</button>
                <input title="Bran Stark" type="text" data-hotkey="b" />
                <button title="Sansa Stark" data-hotkey="c" style="display: none;" />
                <TestComponent />
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("Hodor");
        }
    }
    await mountWithCleanup(MyComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command span:first-child")).toEqual(["Aria stark", "Bran stark"]);

    // Click on first command
    await contains("#o_command_0").click();
    expect(".o_command_palette").toHaveCount(0);

    // Reopen palette
    await press(["Control", "k"]);
    await animationFrame();

    // Click on second command
    expect("input[title='Bran Stark']").not.toBeFocused();
    await contains("#o_command_1").click();
    expect(".o_command_palette").toHaveCount(0);
    expect("input[title='Bran Stark']").toBeFocused();

    // only step should come from the first command execution
    expect.verifySteps(["Hodor"]);
});

test("access to hotkeys from the command palette", async () => {
    const hotkey = "a";
    getService("command").add("A", () => expect.step("A"), {
        hotkey,
    });

    class MyComponent extends Component {
        static components = { TestComponent };
        static template = xml`
            <div>
                <button title="B" data-hotkey="b" t-on-click="onClickB">visible</button>
                <button title="C" data-hotkey="c" t-on-click="onClickC">visible</button>
                <TestComponent />
            </div>
        `;
        static props = ["*"];
        onClickB() {
            expect.step("B");
        }
        onClickC() {
            expect.step("C");
        }
    }
    await mountWithCleanup(MyComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(".o_command").toHaveCount(3);
    expect(queryAllTexts(".o_command span:first-child")).toEqual(["A", "B", "C"]);

    // Trigger the command a
    await press("a");
    await animationFrame();
    expect(".o_command_palette").toHaveCount(0);

    // Reopen palette
    await press(["Control", "k"]);
    await animationFrame();

    // Trigger the command b
    await press(["alt", "b"]);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(0);

    // Reopen palette
    await press(["Control", "k"]);
    await animationFrame();

    // Trigger the command c
    await press(["alt", "c"]);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(0);

    expect.verifySteps(["A", "B", "C"]);
});

test("can be searched", async () => {
    await mountWithCleanup(TestComponent);

    // Register some commands
    const names = ["Cersei Lannister", "Jaime Lannister", "Tyrion Lannister", "Tywin Lannister"];
    for (const name of names) {
        getService("command").add(name, function action() {});
    }
    await animationFrame();

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(".o_command_palette_search input").toHaveValue("");

    expect(queryAllTexts(".o_command")).toEqual(names);

    // Search something
    await contains(".o_command_palette_search input").edit("jl", { confirm: false });
    await animationFrame();

    expect(queryAllTexts(".o_command")).toEqual(["Jaime Lannister"]);

    // Clear search input
    await contains(".o_command_palette_search input").clear({ confirm: false });
    await animationFrame();

    expect(queryAllTexts(".o_command")).toEqual(names);
});

test("configure the empty message based on the namespace", async () => {
    commandProviderRegistry.add(
        "default",
        {
            namespace: "default",
            provide: () => [],
        },
        { force: true }
    );

    commandProviderRegistry.add("@", {
        namespace: "@",
        provide: () => [],
    });

    commandSetupRegistry.add(
        "default",
        {
            emptyMessage: "Empty Default",
        },
        { force: true }
    );
    commandSetupRegistry.add("@", {
        emptyMessage: "Empty @",
    });

    await mountWithCleanup(TestComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(".o_command_palette_listbox_empty").toHaveText("Empty Default");

    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await animationFrame();
    expect(".o_command_palette_listbox_empty").toHaveText("Empty @");
});

test("footer displays the right tips", async () => {
    commandProviderRegistry.add(
        "default",
        {
            namespace: "default",
            provide: () => [],
        },
        { force: true }
    );

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

    commandSetupRegistry.remove("/");
    commandSetupRegistry.add("default", {}, { force: true });
    commandSetupRegistry.add("@", {
        name: "FirstName",
    });

    await mountWithCleanup(TestComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette_footer").toHaveText("TIP — search for @FirstName");

    // Close palette
    await press("escape");
    commandSetupRegistry.add("!", {
        name: "SecondName",
    });
    // Open palette
    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette_footer").toHaveText("TIP — search for @FirstName and !SecondName");

    // Close palette
    await press("escape");
    commandSetupRegistry.add("#", {
        name: "ThirdName",
    });
    // Open palette
    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette_footer").toHaveText(
        "TIP — search for @FirstName, !SecondName and #ThirdName"
    );
});

test("namespaces display in the footer are still clickable", async () => {
    const action = () => {};
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

    commandSetupRegistry.add("default", {}, { force: true });
    commandSetupRegistry.add("@", {
        name: "users",
    });
    commandSetupRegistry.add("#", {
        name: "channels",
    });
    await mountWithCleanup(TestComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette_footer").toHaveText("TIP — search for @users and #channels");
    expect(queryAllTexts(".o_command")).toEqual([]);

    await contains(".o_command_palette_footer .o_namespace").click();
    await animationFrame();
    expect(".o_command_palette_search .o_namespace").toHaveText("@");
    expect(".o_command_palette_search input").toHaveValue("");
    expect(queryAllTexts(".o_command")).toEqual(["Command@"]);

    await contains(".o_command_palette_search input").edit("Com", { confirm: false });
    await advanceFrame();
    await contains(".o_command_palette_footer .o_namespace:eq(1)").click();
    await animationFrame();
    expect(".o_command_palette_search .o_namespace").toHaveText("#");
    expect(".o_command_palette_search input").toHaveValue("Com");
    expect(queryAllTexts(".o_command")).toEqual(["Command#"]);

    await contains(".o_command_palette_footer .o_namespace:eq(0)").click();
    await animationFrame();
    expect(".o_command_palette_search .o_namespace").toHaveText("@");
    expect(".o_command_palette_search input").toHaveValue("Com");
    expect(queryAllTexts(".o_command")).toEqual(["Command@"]);
});

test("defined multiple providers with the same namespace", async () => {
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

    await mountWithCleanup(TestComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();
    await animationFrame();
    expect(".o_command_palette_search input").toHaveValue("");

    expect(queryAllTexts(".o_command")).toEqual([...defaultNames, ...otherNames]);
});

test("can switch between command providers", async () => {
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

    await mountWithCleanup(TestComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(".o_command_palette_search input").toHaveValue("");

    expect(queryAllTexts(".o_command")).toEqual(defaultNames);

    // Switch to the other provider
    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await advanceFrame();

    expect(queryAllTexts(".o_command")).toEqual(otherNames);

    // Press backspace to recover the default provider
    await press("backspace");
    await advanceTime(1);

    expect(queryAllTexts(".o_command")).toEqual(defaultNames);
});

test("multi level commands", async () => {
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

    await mountWithCleanup(TestComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(".o_command_palette_search input").toHaveValue("");
    expect(".o_command_palette_search input").toHaveProperty(
        "placeholder",
        "Search for a command..."
    );

    expect(queryAllTexts(".o_command")).toEqual(defaultNames);

    await contains(".o_command.focused").click();
    await animationFrame();

    expect(".o_command_palette_search input").toHaveProperty(
        "placeholder",
        "Who is the next King ?"
    );

    expect(queryAllTexts(".o_command")).toEqual(otherNames);
});

test("multi level commands with hotkey", async () => {
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

    await mountWithCleanup(TestComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette_search input").toHaveValue("");
    expect(".o_command_palette_search input").toHaveProperty(
        "placeholder",
        "Search for a command..."
    );

    expect(queryAllTexts(".o_command")).toEqual([[name, hotkey.toUpperCase()].join("\n")]);

    await press("a");
    await animationFrame();

    expect(".o_command_palette_search input").toHaveProperty(
        "placeholder",
        "Who is the next King ?"
    );

    expect(queryAllTexts(".o_command")).toEqual(otherNames);
});

test("command categories", async () => {
    await mountWithCleanup(TestComponent);

    // Register some commands
    function action() {}
    getService("command").add("a", action, { category: "custom-nolabel" });
    getService("command").add("b", action, { category: "custom" });
    getService("command").add("c", action);
    getService("command").add("d", action, { category: "invalid-category" });
    await animationFrame();

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(".o_command_category").toHaveCount(3);
    expect(queryAllTexts(".o_command_category")).toEqual(["a", "b", "c\nd"]);
});

test("data-command-category", async () => {
    class MyComponent extends Component {
        static components = { TestComponent };
        static template = xml`
            <div>
            <div>
                <button title="Aria Stark" data-hotkey="a">visible</button>
                <button title="Bran Stark" data-hotkey="b">visible</button>
            </div>
            <div data-command-category="custom">
                <button title="Robert Baratheon" data-hotkey="r">visible</button>
                <button title="Joffrey Baratheon" data-hotkey="j">visible</button>
            </div>
            <TestComponent />
            </div>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(MyComponent);

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(".o_command").toHaveCount(4);
    expect(
        queryAllTexts(".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child")
    ).toEqual(["Robert baratheon", "Joffrey baratheon"]);
    expect(
        queryAllTexts(".o_command_category:nth-of-type(2) .o_command > a > div > span:first-child")
    ).toEqual(["Aria stark", "Bran stark"]);
});

test("display shortcuts correctly for non-MacOS ", async () => {
    class MyComponent extends Component {
        static components = { TestComponent };
        static template = xml`
            <div>
                <button title="Click" data-hotkey="f">visible</button>
                <TestComponent />
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);

    // Register some commands
    function action() {}
    getService("command").add("a", action);
    getService("command").add("b", action, { hotkey: "alt+b" });
    getService("command").add("c", action, { hotkey: "c" });
    getService("command").add("d", action, {
        hotkey: "control+d",
    });
    getService("command").add("e", action, {
        hotkey: "alt+control+e",
    });
    await animationFrame();

    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(queryAllTexts(".o_command")).toEqual([
        "a",
        "b\nALT + B",
        "c\nC",
        "d\nCONTROL + D",
        "e\nALT + CONTROL + E",
        "Click\nALT + F",
    ]);
});

test("display shortcuts correctly for MacOS ", async () => {
    mockUserAgent("mac");

    class MyComponent extends Component {
        static components = { TestComponent };
        static template = xml`
            <div>
            <button title="Click" data-hotkey="f">visible</button>
            <TestComponent />
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);

    // Register some commands
    function action() {}
    getService("command").add("a", action);
    getService("command").add("b", action, { hotkey: "alt+b" });
    getService("command").add("c", action, { hotkey: "c" });
    getService("command").add("d", action, {
        hotkey: "control+d",
    });
    getService("command").add("e", action, {
        hotkey: "alt+control+e",
    });
    await animationFrame();

    // Open palette
    await press(["meta", "k"]);
    await animationFrame();

    expect(queryAllTexts(".o_command")).toEqual([
        "a",
        "b\nCONTROL + B",
        "c\nC",
        "d\nCOMMAND + D",
        "e\nCONTROL + COMMAND + E",
        "Click\nCONTROL + F",
    ]);
});

test("display shortcuts correctly for non-MacOS with a new overlayModifier", async () => {
    const hotkeyService = registry.category("services").get("hotkey");
    patchWithCleanup(hotkeyService, {
        overlayModifier: "alt+control",
    });

    class MyComponent extends Component {
        static components = { TestComponent };
        static template = xml`
                <div>
                <button title="Click" data-hotkey="a">visible</button>
                <TestComponent />
                </div>
            `;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);
    // Open palette
    await press(["Control", "k"]);
    await animationFrame();

    expect(queryAllTexts(".o_command")).toEqual(["Click\nALT + CONTROL + A"]);
});

test("display shortcuts correctly for MacOS with a new overlayModifier", async () => {
    mockUserAgent("mac");

    const hotkeyService = registry.category("services").get("hotkey");
    patchWithCleanup(hotkeyService, {
        overlayModifier: "alt+control",
    });

    class MyComponent extends Component {
        static components = { TestComponent };
        static template = xml`
            <div>
            <button title="Click" data-hotkey="a">visible</button>
            <TestComponent />
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);
    // Open palette
    await press(["meta", "k"]);
    await animationFrame();

    expect(queryAllTexts(".o_command")).toEqual(["Click\nCONTROL + COMMAND + A"]);
});

test("openMainPalette with onClose", async () => {
    const command = getService("command");
    command.openMainPalette({}, () => {
        expect.step("onClose");
    });
    await mountWithCleanup(TestComponent);

    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);

    await press("escape");
    await animationFrame();
    expect.verifySteps(["onClose"]);
});

test("uses openPalette to modify the config used by the command palette", async () => {
    const action = () => {};
    getService("command").add("Command1", action);

    await mountWithCleanup(TestComponent);

    await press(["Control", "k"]);
    await animationFrame();
    expect(".o_command_palette_search input").toHaveValue("");
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command span:first-child")).toEqual(["Command1"]);

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
    getService("command").openPalette(configCustom);
    await animationFrame();
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command .o_command_name")).toEqual(["Command2"]);
    expect(".o_command_palette_search input").toHaveValue("Command");
});

test("ensure that calling openPalette multiple times successfully loads the last config for the command palette", async () => {
    const providePromise1 = new Deferred();
    const providePromise2 = new Deferred();
    const action = () => {};

    await mountWithCleanup(TestComponent);

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

    getService("command").openPalette(configCustom1);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(0);
    getService("command").openPalette(configCustom2);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(0);
    providePromise1.resolve();
    await animationFrame();
    // First config should not be loaded since a second config was sent.
    expect(".o_command_palette").toHaveCount(0);
    providePromise2.resolve();
    await animationFrame();
    // Second config should be loaded properly.
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command .o_command_name")).toEqual(["Command2"]);
    expect(".o_command_palette_search input").toHaveValue("Command");
});
