// @ts-check

import { expect, getFixture, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    click,
    Deferred,
    edit,
    fill,
    press,
    queryAll,
    queryAllTexts,
    queryOne,
    runAllTimers,
} from "@odoo/hoot-dom";
import { Component, EventBus, xml } from "@odoo/owl";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { CommandPaletteEvent } from "@web/core/events";
import { useCommand } from "@web/ui/commands/command_hook";
import {
    CommandPalette,
    MAX_DISPLAYED_COMMANDS,
} from "@web/ui/commands/command_palette";
import { MainComponentsContainer } from "@web/ui/main_components_container";

class FooterComponent extends Component {
    static template = xml`<span>My footer</span>`;
    static props = ["*"];
}

test("an Enter waiting on a cancelled search cannot execute after palette destruction", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const close = getService("dialog").add(CommandPalette, {
        config: {
            configByNamespace: { default: { debounceDelay: 1000 } },
            providers: [
                {
                    provide: () => [
                        { name: "Run", action: () => expect.step("executed") },
                    ],
                },
            ],
        },
    });
    await animationFrame();
    await contains(".o_command_palette_search input").edit("queued", {
        confirm: false,
    });
    await press("enter");
    await close();
    await animationFrame();
    await advanceTime(1100);
    expect(".o_command_palette").toHaveCount(0);
    expect.verifySteps([]);
});

test("an Enter waiting on a running provider cannot execute after palette destruction", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const done = new Deferred();
    const commands = [{ name: "Run", action: () => expect.step("executed") }];
    const close = getService("dialog").add(CommandPalette, {
        config: {
            providers: [
                {
                    provide: (_env, { searchValue }) => {
                        expect.step(searchValue ? "search started" : "initial");
                        return searchValue ? done : commands;
                    },
                },
            ],
        },
    });
    await animationFrame();
    expect.verifySteps(["initial"]);
    await contains(".o_command_palette_search input").edit("Run", { confirm: false });
    await advanceTime(1);
    expect.verifySteps(["search started"]);
    await press("enter");
    await close();
    await animationFrame();
    done.resolve(commands);
    await animationFrame();
    expect.verifySteps([]);
});

test("closing the palette cancels a queued provider search", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const close = getService("dialog").add(CommandPalette, {
        config: {
            configByNamespace: { default: { debounceDelay: 1000 } },
            providers: [
                {
                    provide: () => {
                        expect.step("provide");
                        return [];
                    },
                },
            ],
        },
    });
    await animationFrame();
    expect.verifySteps(["provide"]);
    await contains(".o_command_palette_search input").edit("queued");
    await close();
    await animationFrame();
    await advanceTime(1100);
    expect.verifySteps([]);
});

test("empty providers", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const config = {
        /** @type {any[]} */
        providers: [],
    };
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette_listbox_empty").toHaveCount(1);
    expect(".o_command_palette_listbox_empty").toHaveText("No result found");
    expect(".o_command_palette_search input").toHaveAttribute(
        "placeholder",
        "Search...",
    );
    expect(".o_command_palette_footer").toHaveCount(0);
});

test("custom empty message", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette_listbox_empty").toHaveCount(1);
    expect(".o_command_palette_listbox_empty").toHaveText(
        configByNamespace["default"].emptyMessage,
    );

    await click(".o_command_palette_search input");
    await edit("@");
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveCount(1);
    expect(".o_command_palette_listbox_empty").toHaveText(
        configByNamespace["@"].emptyMessage,
    );

    await edit("#");
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveCount(1);
    expect(".o_command_palette_listbox_empty").toHaveText(
        configByNamespace["#"].emptyMessage,
    );
});

test("custom debounce delay", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const configByNamespace = {
        "@": {
            debounceDelay: 1000,
        },
        "#": {
            debounceDelay: 500,
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);
    await click(".o_command_palette_search input");
    await fill("com");
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveText("No result found");
    await edit("@");
    await advanceTime(700);
    expect(".o_command").toHaveCount(0);
    await advanceTime(300);
    expect(".o_command").toHaveCount(2);
    await press("backspace");
    await runAllTimers();
    expect(".o_command").toHaveCount(0);
    await edit("#");
    expect(".o_command").toHaveCount(0);
    await advanceTime(500);
    expect(".o_command").toHaveCount(2);
});

test.tags("desktop");
test("concurrency with custom debounce delay", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const configByNamespace = {
        "@": {
            debounceDelay: 1000,
        },
        "#": {
            debounceDelay: 500,
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette .o_namespace").toHaveCount(0);

    await fill("@");
    await animationFrame();
    expect(".o_command_palette .o_namespace").toHaveText("@");
    expect(queryAllTexts(".o_command")).toEqual([]);

    await edit("#");
    await animationFrame();
    expect(".o_command_palette .o_namespace").toHaveText("#");
    await advanceTime(500);
    expect(queryAllTexts(".o_command")).toEqual(["Command#"]);

    await advanceTime(500);
    expect(".o_command_palette .o_namespace").toHaveText("#");
    expect(queryAllTexts(".o_command")).toEqual(["Command#"]);
});

test("custom placeholder", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette_listbox_empty").toHaveCount(1);
    expect(".o_command_palette_search input").toHaveAttribute(
        "placeholder",
        "default placeholder",
    );

    await click(".o_command_palette_search input");
    await edit("@");
    await runAllTimers();
    expect(".o_command_palette_search input").toHaveAttribute(
        "placeholder",
        "@ placeholder",
    );
});

test("add a footer", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const config = {
        providers: [],
        FooterComponent,
    };
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette_footer").toHaveCount(1);
    expect(".o_command_palette_footer").toHaveText("My footer");
});

test("command with a Custom Component", async () => {
    class CustomComponent extends Component {
        static template = xml`
            <div class="o_command_custom">
                <span t-esc="props.name"/>
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2"]);
    expect(queryAllTexts(".o_command .o_command_default")).toEqual(["Command2"]);
    expect(queryAllTexts(".o_command .o_command_custom")).toEqual(["Command1"]);
});

test("multi namespace with provider", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command_palette .o_namespace").toHaveCount(0);
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2"]);

    await click(".o_command_palette_search input");
    await edit("@");
    await runAllTimers();
    expect(".o_command_palette .o_namespace").toHaveText("@");
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command3", "Command4"]);
});

test("apply a fuzzysearch on the namespace default not on the others", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2"]);
    await click(".o_command_palette_search input");
    await edit("c1");
    await runAllTimers();
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Command1"]);

    await edit("@");
    await runAllTimers();
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command3", "Command4"]);
    await edit("@c3");
    await runAllTimers();
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command3", "Command4"]);
});

test("multi provider with the same namespace", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(4);
    expect(queryAllTexts(".o_command")).toEqual([
        "Command1",
        "Command2",
        "Command3",
        "Command4",
    ]);
});

test("check the concurrency during a research", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const imSearchDef = new Deferred();
    const provide = async (env, options) => {
        if (options.searchValue) {
            await imSearchDef;
        }
        return [
            {
                name: "a",
                action: () => {
                    expect.step("a");
                },
            },
            {
                name: "b",
                action: () => {
                    expect.step("b");
                },
            },
        ];
    };
    const providers = [{ namespace: "default", provide }];
    const config = {
        providers,
    };
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(2);

    await click(".o_command_palette_search input");
    await edit("b");
    await runAllTimers();
    await press("enter");
    await animationFrame();
    expect.verifySteps([]);

    imSearchDef.resolve();
    await animationFrame();
    expect.verifySteps(["b"]);
});

test("Enter still executes after an in-flight search is superseded by a reconfigure", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const bus = new EventBus();
    const searchDef = new Deferred();
    const provide = async (env, options) => {
        if (options.searchValue) {
            await searchDef;
        }
        return [
            {
                name: "cmd",
                action: () => expect.step("executed"),
            },
        ];
    };
    const config = { providers: [{ namespace: "default", provide }] };
    getService("dialog").add(CommandPalette, { config, bus });
    await animationFrame();
    expect(".o_command").toHaveCount(1);

    await click(".o_command_palette_search input");
    await edit("a");
    await runAllTimers();

    bus.trigger(CommandPaletteEvent.SET_CONFIG, config);
    await animationFrame();

    searchDef.resolve();
    await animationFrame();
    await runAllTimers();

    await press("enter");
    await animationFrame();
    expect.verifySteps(["executed"]);
    expect(".o_command_palette .fa-spin").toHaveCount(0);
});

test("open the command palette with a searchValue already in the searchbar", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command_palette_search input").toHaveValue("C1");
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Command1"]);
});

test.tags("desktop");
test("command palette keeps the same top position when its content changes", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(4);
    expect(".o_command_palette").toHaveRect({ top: 120 });
    await click(".o_command_palette_search input");
    await edit("z");
    await runAllTimers();
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette").toHaveRect({ top: 120 });
});

test("open the command palette with a namespace already in the searchbar", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command_palette .o_namespace").toHaveText("@");
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command3", "Command4"]);
});

test("open the command palette with a searchValue with a namespace", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command_palette .o_namespace").toHaveText("@");
    expect(".o_command_palette_search input").toHaveValue("Test");
    expect(queryAllTexts(".o_command")).toEqual(["Command3", "Command4"]);
});

test("open the command palette with a searchValue without namespace", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command_palette .o_namespace").toHaveCount(0);
    expect(".o_command_palette_search input").toHaveValue("Command1");
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Command1"]);
});

test("multi provider with categories", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(3);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2", "Command3"]);
    expect(".o_command_category").toHaveCount(3);
    expect(
        queryAllTexts(
            ".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child",
        ),
    ).toEqual(["Command1"]);
    expect(
        queryAllTexts(
            ".o_command_category:nth-of-type(2) .o_command > a > div > span:first-child",
        ),
    ).toEqual(["Command2"]);
    expect(
        queryAllTexts(
            ".o_command_category:nth-of-type(3) .o_command > a > div > span:first-child",
        ),
    ).toEqual(["Command3"]);

    await click(".o_command_palette_search input");
    await edit("@");
    await runAllTimers();
    expect(".o_command").toHaveCount(4);
    expect(queryAllTexts(".o_command")).toEqual([
        "Command6",
        "Command7",
        "Command5",
        "Command4",
    ]);
    expect(".o_command_category").toHaveCount(3);
    expect(
        queryAllTexts(
            ".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child",
        ),
    ).toEqual(["Command6", "Command7"]);
    expect(
        queryAllTexts(
            ".o_command_category:nth-of-type(2) .o_command > a > div > span:first-child",
        ),
    ).toEqual(["Command5"]);
    expect(
        queryAllTexts(
            ".o_command_category:nth-of-type(3) .o_command > a > div > span:first-child",
        ),
    ).toEqual(["Command4"]);
});

test("don't display by categories if there is a search value", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(3);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2", "Command3"]);
    expect(".o_command_category").toHaveCount(3);

    await click(".o_command_palette_search input");
    await edit("c");
    await runAllTimers();
    expect(".o_command").toHaveCount(3);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2", "Command3"]);

    expect(
        queryAllTexts(
            ".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child",
        ),
    ).toEqual(["Command1", "Command2", "Command3"]);
});

test("click on command", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const commands = [
        {
            name: "Command1",
            action: () => {
                expect.step("C1");
            },
        },
        {
            name: "Command2",
            action: () => {
                expect.step("C2");
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2"]);
    expect(".o_command.focused").toHaveText(commands[0].name);
    await contains(".o_command.focused").click();
    expect.verifySteps(["C1"]);
});

test("press enter on command", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const commands = [
        {
            name: "Command1",
            action: () => {
                expect.step("C1");
            },
        },
        {
            name: "Command2",
            action: () => {
                expect.step("C2");
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2"]);
    expect(".o_command.focused").toHaveText(commands[0].name);
    await press("arrowdown");
    await animationFrame();
    await press("enter");
    await animationFrame();

    expect.verifySteps(["C2"]);
});

test("keyboard navigation scroll", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });

    const isVisible = (el) => {
        const elementRect = queryOne(el).getBoundingClientRect();
        const scrollableRect = queryOne(
            ".o_command_palette_listbox",
        ).getBoundingClientRect();
        return (
            elementRect.bottom <= scrollableRect.bottom &&
            elementRect.top >= scrollableRect.top
        );
    };

    const getFocusedCommandBorderState = () => {
        const elementRect = queryOne(".o_command.focused").getBoundingClientRect();
        const scrollableRect = queryOne(
            ".o_command_palette_listbox",
        ).getBoundingClientRect();
        return {
            top: elementRect.top === scrollableRect.top,
            bottom: elementRect.bottom === scrollableRect.bottom,
        };
    };

    await animationFrame();
    queryAll(".o_command").forEach((e) => (e.style.height = "50px"));
    queryOne(".o_command_palette_listbox").style.maxHeight = "150px";
    queryOne(".o_command_category").style.padding = "0";
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(4);

    expect(isVisible("#o_command_0")).toBe(true);
    expect(isVisible("#o_command_1")).toBe(true);
    expect(isVisible("#o_command_2")).toBe(true);
    expect(isVisible("#o_command_3")).not.toBe(true);
    expect(getFocusedCommandBorderState()).toEqual(
        {
            top: true,
            bottom: false,
        },
        { message: "the focus is at the top border" },
    );

    await press("arrowdown");
    await animationFrame();
    expect(isVisible("#o_command_0")).toBe(true);
    expect(isVisible("#o_command_1")).toBe(true);
    expect(isVisible("#o_command_2")).toBe(true);
    expect(isVisible("#o_command_3")).not.toBe(true);
    expect(getFocusedCommandBorderState()).toEqual(
        {
            top: false,
            bottom: false,
        },
        { message: "the focus does not reach a border" },
    );

    await press("arrowdown");
    await animationFrame();
    expect(isVisible("#o_command_0")).toBe(true);
    expect(isVisible("#o_command_1")).toBe(true);
    expect(isVisible("#o_command_2")).toBe(true);
    expect(isVisible("#o_command_3")).not.toBe(true);
    expect(getFocusedCommandBorderState()).toEqual(
        {
            top: false,
            bottom: true,
        },
        { message: "the focus has reached the bottom border" },
    );

    await press("arrowdown");
    await animationFrame();
    expect(isVisible("#o_command_0")).not.toBe(true);
    expect(isVisible("#o_command_1")).toBe(true);
    expect(isVisible("#o_command_2")).toBe(true);
    expect(isVisible("#o_command_3")).toBe(true);
    expect(getFocusedCommandBorderState()).toEqual(
        {
            top: false,
            bottom: true,
        },
        { message: "the focus is still at the bottom border" },
    );

    await press("arrowup");
    await animationFrame();
    expect(isVisible("#o_command_0")).not.toBe(true);
    expect(isVisible("#o_command_1")).toBe(true);
    expect(isVisible("#o_command_2")).toBe(true);
    expect(isVisible("#o_command_3")).toBe(true);
    expect(getFocusedCommandBorderState()).toEqual(
        {
            top: false,
            bottom: false,
        },
        { message: "the focus does not reach a border" },
    );

    await press("arrowup");
    await animationFrame();
    expect(isVisible("#o_command_0")).not.toBe(true);
    expect(isVisible("#o_command_1")).toBe(true);
    expect(isVisible("#o_command_2")).toBe(true);
    expect(isVisible("#o_command_3")).toBe(true);
    expect(getFocusedCommandBorderState()).toEqual(
        {
            top: true,
            bottom: false,
        },
        { message: "the focus has reached the top border" },
    );

    await press("arrowup");
    await animationFrame();
    expect(isVisible("#o_command_0")).toBe(true);
    expect(isVisible("#o_command_1")).toBe(true);
    expect(isVisible("#o_command_2")).toBe(true);
    expect(isVisible("#o_command_3")).not.toBe(true);
    expect(getFocusedCommandBorderState()).toEqual(
        {
            top: true,
            bottom: false,
        },
        { message: "the focus is still at the top border" },
    );
});

test("multi level command", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const configByNamespace = {
        default: {
            emptyMessage: "Empty Default",
            placeholder: "placeholder test",
        },
    };
    const commands = [
        {
            name: "Command1",
            action: () => ({
                providers: [
                    { provide: () => [{ name: "Command lvl2", action: () => {} }] },
                ],
            }),
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    await click(".o_command_palette_search input");
    await edit("empty");
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveText("Empty Default");
    expect(".o_command_palette_search input").toHaveAttribute(
        "placeholder",
        "placeholder test",
    );
    expect(".o_command_palette_footer").toHaveCount(1);
    expect(".o_command_palette_footer").toHaveText("My footer");

    await edit("");
    await runAllTimers();
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Command1"]);
    expect(".o_command.focused").toHaveText(commands[0].name);
    await press("enter");
    await animationFrame();
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Command lvl2"]);

    await edit("empty");
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveText("No result found");
    expect(".o_command_palette_search input").toHaveAttribute(
        "placeholder",
        "Search...",
    );
    expect(".o_command_palette_footer").toHaveCount(0);
});

test.tags("desktop");
test("command palette dialog can be rendered and closed on outside click", async () => {
    await mountWithCleanup(MainComponentsContainer);

    const config = {
        /** @type {any[]} */
        providers: [],
    };
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);

    await contains(getFixture()).click();
    await animationFrame();
    expect(".o_command_palette").toHaveCount(0);
});

test("navigate in the command palette with the arrows", async () => {
    expect.assertions(6);

    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command.focused").toHaveText(commands[0].name);

    await press("arrowdown");
    await animationFrame();
    expect(".o_command.focused").toHaveText(commands[1].name);

    await press("arrowdown");
    await animationFrame();
    expect(".o_command.focused").toHaveText(commands[2].name);

    await press("arrowdown");
    await animationFrame();
    expect(".o_command.focused").toHaveText(commands[0].name);

    await press("arrowup");
    await animationFrame();
    expect(".o_command.focused").toHaveText(commands[2].name);

    await press("arrowup");
    await animationFrame();
    expect(".o_command.focused").toHaveText(commands[1].name);
});

test("navigate in the command palette with an empty list", async () => {
    expect.assertions(6);

    await mountWithCleanup(MainComponentsContainer);
    const providers = [
        {
            provide: () => [],
        },
    ];
    const config = {
        providers,
    };
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette_listbox_empty").toHaveCount(1);

    await press("arrowdown");
    await animationFrame();
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette_listbox_empty").toHaveCount(1);

    await press("arrowup");
    await animationFrame();
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette_listbox_empty").toHaveCount(1);
});

test("bold the searchValue on the commands", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(5);
    expect(queryAllTexts(".o_command .fw-bolder")).toEqual([]);

    await click(".o_command_palette_search input");
    await edit("@test");
    await runAllTimers();
    expect(".o_command").toHaveCount(5);
    expect(
        queryAll(".o_command").map((command) =>
            queryAllTexts(".o_command_name .fw-bolder", { root: command }),
        ),
    ).toEqual([["Test"], ["test"], ["test"], ["Test"], ["TeSt", "Test", "TEST"]]);
});

test("bold the searchValue on the commands with special char", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const action = () => {};
    const providers = [
        {
            namespace: "/",
            provide: () => [
                {
                    name: "Test&",
                    action,
                },
                {
                    name: "Research & Development",
                    action,
                },
            ],
        },
    ];
    const config = {
        searchValue: "/",
        providers,
    };
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Test&", "Research & Development"]);
    expect(queryAllTexts(".o_command .fw-bolder")).toEqual([]);

    await click(".o_command_palette_search input");
    await edit("/a");
    await runAllTimers();
    expect(".o_command").toHaveCount(2);
    expect(
        queryAll(".o_command").map((command) =>
            queryAllTexts(".o_command_name .fw-bolder", { root: command }),
        ),
    ).toEqual([[], ["a"]]);

    await click(".o_command_palette_search input");
    await edit("/&");
    await runAllTimers();
    expect(".o_command").toHaveCount(2);
    expect(
        queryAll(".o_command").map((command) =>
            queryAllTexts(".o_command_name .fw-bolder", { root: command }),
        ),
    ).toEqual([["&"], ["&"]]);
});

test("bold the searchValue on the commands with accents", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const action = () => {};
    const providers = [
        {
            provide: () => [
                {
                    name: "Cédric",
                    action,
                },
            ],
        },
    ];
    const config = {
        searchValue: "èd",
        providers,
    };
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Cédric"]);
    expect(queryAllTexts(".o_command .fw-bolder")).toEqual(["éd"]);
});

test("remove namespace with backspace", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    await click(".o_command_palette_search input");
    await edit("@");
    await runAllTimers();
    expect(".o_command_palette .o_namespace").toHaveText("@");

    await press("backspace");
    await animationFrame();
    expect(".o_command_palette .o_namespace").toHaveCount(0);
    expect(".o_command_palette_search input").toHaveValue("");

    await edit("@NotEmpty");
    await runAllTimers();
    expect(".o_command_palette .o_namespace").toHaveText("@");
    expect(".o_command_palette_search input").toHaveValue("NotEmpty");

    await press("backspace");
    await animationFrame();
    expect(".o_command_palette .o_namespace").toHaveText("@");

    await edit("@");
    await runAllTimers();
    expect(".o_command_palette .o_namespace").toHaveText("@");

    await press("backspace", { repeat: true });
    expect(".o_command_palette .o_namespace").toHaveText("@");
});

test("checks that href is correctly used", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const providers = [
        {
            namespace: "@",
            provide: () => [
                {
                    name: "Command with link",
                    action: () => {
                        expect.step("command_with_link_clicked");
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    patchWithCleanup(browser, {
        open: (href) => {
            expect.step(href.toString());
            return window;
        },
    });
    await animationFrame();
    await click(".o_command_palette_search input");
    await edit("@");
    await runAllTimers();
    expect(".o_command_palette .o_command:eq(0) a").toHaveAttribute(
        "href",
        "https://www.odoo.com",
    );
    await press("control+enter");
    await animationFrame();
    expect.verifySteps(["https://www.odoo.com"]);
    expect(".o_command_palette .o_command:eq(1) a").not.toHaveAttribute("href");
    await contains(".o_command_palette .o_command:eq(0)").click();
    expect.verifySteps(["command_with_link_clicked"]);
});

test("searchValue must not change without edition", async () => {
    const provideDef = new Deferred();

    await mountWithCleanup(MainComponentsContainer);
    const providers = [
        {
            provide: async (env, { searchValue }) => {
                if (searchValue === "abc") {
                    await provideDef;
                }
                return [
                    {
                        name: searchValue,
                        action: () => {},
                    },
                ];
            },
        },
    ];
    const config = {
        providers,
    };
    getService("dialog").add(CommandPalette, {
        config,
    });

    await animationFrame();

    await click(".o_command_palette_search input");
    await edit("abc");
    expect(".o_command_palette_search input").toHaveValue("abc");

    await edit("deb");
    expect(".o_command_palette_search input").toHaveValue("deb");

    provideDef.resolve();
    expect(".o_command_palette_search input").toHaveValue("deb");

    await runAllTimers();
    expect(".o_command_palette_search input").toHaveValue("deb");
});

test("display spinner while loading results from providers", async () => {
    const provideDef = new Deferred();
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(CommandPalette, {
        config: {
            providers: [
                {
                    namespace: "?",
                    provide: async (env, { searchValue }) => {
                        await provideDef;
                        return [];
                    },
                },
            ],
        },
    });

    await animationFrame();
    expect(".o_command_palette_search i.oi.oi-search").toHaveCount(1);
    expect(".o_command_palette_search i.fa-solid.fa-circle-notch").toHaveCount(0);
    await click(".o_command_palette_search input");
    await edit("? blabla");
    await runAllTimers();
    expect(".o_command_palette_search i.oi.oi-search").toHaveCount(0);
    expect(".o_command_palette_search i.fa-solid.fa-circle-notch").toHaveCount(1);
    provideDef.resolve();
    await animationFrame();
    expect(".o_command_palette_search i.oi.oi-search").toHaveCount(1);
    expect(".o_command_palette_search i.fa-solid.fa-circle-notch").toHaveCount(0);
});

test("a throwing command action closes the palette and surfaces the error", async () => {
    expect.errors(1);
    await mountWithCleanup(MainComponentsContainer);
    const config = {
        providers: [
            {
                provide: () => [
                    {
                        name: "BoomCommand",
                        action: () => {
                            throw new Error("action boom");
                        },
                    },
                ],
            },
        ],
    };
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(1);

    await press("enter");
    await animationFrame();
    expect(".o_command_palette").toHaveCount(0);
    expect.verifyErrors(["Error: action boom"]);
});

test("category grouping is preserved while an async provider reloads", async () => {
    let provideDef = new Deferred();
    const action = () => {};
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(CommandPalette, {
        config: {
            configByNamespace: {
                "?": {
                    categories: ["cat1", "cat2"],
                },
            },
            providers: [
                {
                    namespace: "?",
                    provide: async () => {
                        await provideDef;
                        return [
                            { name: "Command1", action, category: "cat1" },
                            { name: "Command2", action, category: "cat2" },
                            { name: "Command3", action },
                        ];
                    },
                },
            ],
        },
    });

    await animationFrame();
    await click(".o_command_palette_search input");
    await edit("?");
    await runAllTimers();
    provideDef.resolve();
    await animationFrame();
    expect(".o_command_category").toHaveCount(3);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2", "Command3"]);

    provideDef = new Deferred();
    await edit("? a");
    await runAllTimers();
    expect(".o_command_palette_search i.fa-solid.fa-circle-notch").toHaveCount(1);
    expect(".o_command_category").toHaveCount(3);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2", "Command3"]);

    provideDef.resolve();
    await animationFrame();
    expect(".o_command_category").toHaveCount(3);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2", "Command3"]);
});

/** @param {any[] | (() => any[])} commands */
async function mountPalette(commands) {
    await mountWithCleanup(MainComponentsContainer);
    /** @type {any} */
    let palette;
    patchWithCleanup(CommandPalette.prototype, {
        setup() {
            super.setup();
            palette = this;
        },
    });
    const provide = typeof commands === "function" ? commands : () => commands;
    getService("dialog").add(CommandPalette, {
        config: { providers: [{ provide }] },
    });
    await animationFrame();
    return palette;
}

test("an index that is not a position selects nothing instead of throwing", async () => {
    const palette = await mountPalette([
        { name: "cmd a", action: () => {} },
        { name: "cmd b", action: () => {} },
    ]);
    expect(palette.selectedCommand.name).toBe("cmd a");

    for (const bad of [undefined, NaN, -2, -1, 2, 99, 1.5, null]) {
        palette.selectCommand(bad);
        expect(palette.selectedCommand).toBe(null);
    }

    palette.selectCommand(1);
    expect(palette.selectedCommand.name).toBe("cmd b");
});

test("the highlighted command follows the list it is an index into", async () => {
    const palette = await mountPalette([
        { name: "cmd a", action: () => {} },
        { name: "cmd b", action: () => {} },
        { name: "cmd c", action: () => {} },
    ]);
    palette.selectCommand(2);
    expect(palette.selectedCommand.name).toBe("cmd c");

    palette.state.commands = palette.state.commands.slice(0, 1);
    expect(palette.selectedCommand).toBe(null);
});

test("a search that fails is reported, not swallowed", async () => {
    expect.errors(1);
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(CommandPalette, {
        config: {
            providers: [
                {
                    provide: (env, { searchValue }) =>
                        searchValue
                            ? /** @type {any} */ (undefined)
                            : [{ name: "cmd a", action: () => {} }],
                },
            ],
        },
    });
    await animationFrame();
    expect(queryAllTexts(".o_command_name")).toEqual(["cmd a"]);

    await click(".o_command_palette_search input");
    await edit("a");
    await runAllTimers();
    await animationFrame();

    expect(".o_command_palette").toHaveCount(1);
    expect(".fa-circle-notch").toHaveCount(0);
    expect.verifyErrors([/Cannot read properties of undefined/]);
});

test("two commands that cannot render in one pass both lose their row", async () => {
    expect.errors(2);
    let poison = false;
    class Poisoned extends Component {
        static template = xml`<span class="poisoned" t-att-data-check="check"/>`;
        static props = ["*"];
        get check() {
            if (poison) {
                throw new Error(`poisoned ${this.props.which}`);
            }
            return "";
        }
    }
    const palette = await mountPalette(() => [
        { name: "cmd a", action: () => {} },
        { name: "cmd b", action: () => {}, Component: Poisoned, props: { which: "b" } },
        { name: "cmd c", action: () => {}, Component: Poisoned, props: { which: "c" } },
        { name: "cmd d", action: () => {} },
    ]);
    expect(".poisoned").toHaveCount(2);

    poison = true;
    await click(".o_command_palette_search input");
    await edit("cmd");
    await runAllTimers();
    await animationFrame();
    await animationFrame();

    expect(".o_command_palette").toHaveCount(1);
    expect(".poisoned").toHaveCount(0);
    expect(queryAllTexts(".o_command_name")).toEqual(["cmd a", "cmd d"]);
    expect(palette.state.commands.map((c) => c.index)).toEqual([0, 1]);
    expect(queryAll(".o_command").map((el) => el.id)).toEqual([
        "o_command_0",
        "o_command_1",
    ]);
    expect.verifyErrors([/poisoned b/, /poisoned c/]);
});

test("opening the palette asks each provider once", async () => {
    await mountWithCleanup(MainComponentsContainer);
    await animationFrame();
    let calls = 0;
    getService("dialog").add(CommandPalette, {
        config: {
            providers: [
                {
                    provide: () => {
                        calls++;
                        return [{ name: "cmd a", action: () => {} }];
                    },
                },
            ],
        },
    });
    await animationFrame();
    await animationFrame();
    expect(queryAllTexts(".o_command_name")).toEqual(["cmd a"]);
    expect(calls).toBe(1);
});

test("a failing initial search is reported and leaves the palette usable", async () => {
    expect.errors(1);
    await mountWithCleanup(MainComponentsContainer);
    await animationFrame();
    let calls = 0;
    getService("dialog").add(CommandPalette, {
        config: {
            providers: [
                {
                    provide: () =>
                        calls++
                            ? [{ name: "cmd a", action: () => {} }]
                            : /** @type {any} */ (undefined),
                },
            ],
        },
    });
    await animationFrame();
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".fa-circle-notch").toHaveCount(0);

    await click(".o_command_palette_search input");
    await edit("a");
    await runAllTimers();
    await animationFrame();
    expect(queryAllTexts(".o_command_name")).toEqual(["cmd a"]);
    expect.verifyErrors([/Cannot read properties of undefined/]);
});

test("a row that survives a search keeps its component", async () => {
    let setups = 0;
    class Counted extends Component {
        static template = xml`<span class="counted" t-esc="props.name"/>`;
        static props = ["*"];
        setup() {
            setups++;
        }
    }
    await mountPalette(() => [
        { name: "cmd a", action: () => {}, Component: Counted, props: {} },
        { name: "cmd b", action: () => {}, Component: Counted, props: {} },
        { name: "other", action: () => {}, Component: Counted, props: {} },
    ]);
    expect(".counted").toHaveCount(3);
    expect(setups).toBe(3);

    await click(".o_command_palette_search input");
    await edit("cmd");
    await runAllTimers();
    await animationFrame();

    expect(queryAllTexts(".counted")).toEqual(["cmd a", "cmd b"]);
    expect(setups).toBe(3);
});

test("one command that cannot render loses its row, not the palette", async () => {
    expect.errors(1);
    let poison = false;
    class Poisoned extends Component {
        static template = xml`<span class="poisoned" t-att-data-check="check"/>`;
        static props = ["*"];
        get check() {
            if (poison) {
                throw new Error("provider component blew up");
            }
            return "";
        }
    }
    await mountWithCleanup(MainComponentsContainer);
    /** @type {any} */
    let palette;
    patchWithCleanup(CommandPalette.prototype, {
        setup() {
            super.setup();
            palette = this;
        },
    });
    getService("dialog").add(CommandPalette, {
        config: {
            providers: [
                {
                    provide: () => [
                        { name: "cmd a", action: () => {} },
                        {
                            name: "cmd b",
                            action: () => {},
                            Component: Poisoned,
                            props: {},
                        },
                        { name: "cmd c", action: () => {} },
                        { name: "cmd d", action: () => {} },
                    ],
                },
            ],
        },
    });
    await animationFrame();
    expect(".o_command").toHaveCount(4);
    expect(".poisoned").toHaveCount(1);

    poison = true;
    await click(".o_command_palette_search input");
    await edit("cmd");
    await runAllTimers();
    await animationFrame();

    expect(".o_command_palette").toHaveCount(1);
    expect(".poisoned").toHaveCount(0);
    expect(queryAllTexts(".o_command_name")).toEqual(["cmd a", "cmd c", "cmd d"]);

    expect(palette.state.commands.map((c) => c.index)).toEqual([0, 1, 2]);
    expect(queryAll(".o_command").map((el) => el.id)).toEqual([
        "o_command_0",
        "o_command_1",
        "o_command_2",
    ]);
    palette.selectCommand(2);
    expect(palette.selectedCommand.name).toBe("cmd d");
    expect.verifyErrors([/provider component blew up/]);
});

test("an item that throws before the palette mounts costs one attempt, not six", async () => {
    expect.errors(1);
    let provideCalls = 0;
    class Poisoned extends Component {
        static template = xml`<span class="poisoned"/>`;
        static props = ["*"];
        setup() {
            throw new Error("broken on first render");
        }
    }
    const palette = await mountPalette(() => {
        provideCalls++;
        return [
            { name: "cmd a", action: () => {} },
            { name: "cmd b", action: () => {}, Component: Poisoned, props: {} },
            { name: "cmd c", action: () => {} },
        ];
    });
    await animationFrame();

    expect(".o_command_palette").toHaveCount(1);
    expect(queryAllTexts(".o_command_name")).toEqual(["cmd a", "cmd c"]);
    expect(palette.state.commands.map((c) => c.index)).toEqual([0, 1]);
    expect(provideCalls).toBe(2);
    expect.verifyErrors([/broken on first render/]);
});

test("hotkey props reach the item that renders them and no other", async () => {
    class Owner extends Component {
        static template = xml`<div class="owner"/>`;
        static props = {};
        setup() {
            useCommand("with options only", () => {}, {
                hotkeyOptions: { bypassEditableProtection: true },
            });
            useCommand("with a hotkey", () => {}, {
                hotkey: "alt+j",
                hotkeyOptions: { bypassEditableProtection: true },
            });
        }
    }
    await mountWithCleanup(MainComponentsContainer);
    await mountWithCleanup(Owner);
    getService("command").openMainPalette();
    await animationFrame();
    await runAllTimers();
    await animationFrame();

    expect(".o_command_palette").toHaveCount(1);
    expect(queryAllTexts(".o_command_name")).toInclude("with options only");
    expect(queryAllTexts(".o_command_name")).toInclude("with a hotkey");
    expect(".o_command_hotkey kbd").toHaveCount(2);
    await press("escape");
});

test("a command that cannot render is dropped, and its namesake is not", async () => {
    expect.errors(1);
    /** @type {any} */
    let palette;
    patchWithCleanup(CommandPalette.prototype, {
        setup() {
            super.setup();
            palette = this;
        },
    });
    class RecordItem extends Component {
        static template = xml`<span class="o_command_default" t-esc="props.name"/>`;
        static props = ["*"];
    }
    const openRecord = (/** @type {number} */ id) => ({
        name: "Open record",
        category: "default",
        action: () => {},
        Component: RecordItem,
        props: { record: { id } },
    });
    const records = [openRecord(1), openRecord(2)];
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(CommandPalette, {
        config: { providers: [{ provide: () => records }] },
    });
    await animationFrame();
    expect(palette.state.commands).toHaveLength(2);

    palette.handleCommandError(palette.state.commands[0], new Error("cannot render"));
    expect(
        palette.state.commands.map((/** @type {any} */ c) => c.props.record.id),
    ).toEqual([2], { message: "only the one that threw leaves the list" });

    await palette.setCommands("default", { searchValue: "" });
    expect(
        palette.state.commands.map((/** @type {any} */ c) => c.props.record.id),
    ).toEqual([2], {
        message: "the working namesake survives the broken-command filter",
    });
    await animationFrame();
    expect.verifyErrors(["cannot render"]);
});

/**
 * @param {number} n
 * @returns {Promise<string[]>}
 */
async function truncationNoticeFor(n) {
    const commands = Array.from({ length: n }, (_, i) => ({
        name: `Command ${i}`,
        action: () => {},
    }));
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(CommandPalette, {
        config: { providers: [{ provide: () => commands }] },
    });
    await animationFrame();
    return queryAllTexts(".o_command_palette_truncated");
}

test("nothing is hidden at the display limit, so nothing is said", async () => {
    expect(await truncationNoticeFor(MAX_DISPLAYED_COMMANDS)).toEqual([]);
});

test("one result over the limit is one result, not '1 more results'", async () => {
    expect(await truncationNoticeFor(MAX_DISPLAYED_COMMANDS + 1)).toEqual([
        "1 more result — refine your search",
    ]);
});

test("two or more over the limit reads in the plural", async () => {
    expect(await truncationNoticeFor(MAX_DISPLAYED_COMMANDS + 2)).toEqual([
        "2 more results — refine your search",
    ]);
});
