import { expect, getFixture, test } from "@odoo/hoot";
import { press, queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { Deferred, advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { Component, xml } from "@odoo/owl";

import { CommandPalette } from "@web/core/commands/command_palette";
import { MainComponentsContainer } from "@web/core/main_components_container";

class FooterComponent extends Component {
    static template = xml`<span>My footer</span>`;
    static props = ["*"];
}

test("empty providers", async () => {
    await mountWithCleanup(MainComponentsContainer);
    const config = {
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
    expect(".o_command_palette_search input").toHaveAttribute("placeholder", "Search...");
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
        configByNamespace["default"].emptyMessage
    );

    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveCount(1);
    expect(".o_command_palette_listbox_empty").toHaveText(configByNamespace["@"].emptyMessage);

    await contains(".o_command_palette_search input").edit("#", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveCount(1);
    expect(".o_command_palette_listbox_empty").toHaveText(configByNamespace["#"].emptyMessage);
});

test("custom debounce delay", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);
    await contains(".o_command_palette_search input").edit("com", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveText("No result found");
    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await advanceTime(100);
    expect(".o_command").toHaveCount(0);
    await advanceTime(100);
    expect(".o_command").toHaveCount(2);
    await press("backspace");
    await animationFrame();
    expect(".o_command").toHaveCount(0);
    await contains(".o_command_palette_search input").edit("#", { confirm: false });
    expect(".o_command").toHaveCount(0);
    await advanceTime(100);
    expect(".o_command").toHaveCount(2);
});

test("concurrency with custom debounce delay", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(0);
    expect(".o_command_palette .o_namespace").toHaveCount(0);

    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await animationFrame();
    expect(".o_command_palette .o_namespace").toHaveText("@");
    expect(queryAllTexts(".o_command")).toEqual([]);

    await contains(".o_command_palette_search input").edit("#", { confirm: false });
    expect(".o_command_palette .o_namespace").toHaveText("#");
    await advanceTime(100);
    expect(queryAllTexts(".o_command")).toEqual(["Command#"]);

    await advanceTime(100);
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
    expect(".o_command_palette_search input").toHaveAttribute("placeholder", "default placeholder");

    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette_search input").toHaveAttribute("placeholder", "@ placeholder");
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

    await contains(".o_command_palette_search input").edit("@", { confirm: false });
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
    await contains(".o_command_palette_search input").edit("c1", { confirm: false });
    await runAllTimers();
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Command1"]);

    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await runAllTimers();
    expect(".o_command").toHaveCount(2);
    expect(queryAllTexts(".o_command")).toEqual(["Command3", "Command4"]);
    await contains(".o_command_palette_search input").edit("@c3", { confirm: false });
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
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2", "Command3", "Command4"]);
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

    await contains(".o_command_palette_search input").edit("b", { confirm: false });
    await runAllTimers();
    await press("enter");
    await animationFrame();
    expect.verifySteps([]);

    imSearchDef.resolve();
    await animationFrame();
    expect.verifySteps(["b"]);
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
    await contains(".o_command_palette_search input").edit("z", { confirm: false });
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
        queryAllTexts(".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child")
    ).toEqual(["Command1"]);
    expect(
        queryAllTexts(".o_command_category:nth-of-type(2) .o_command > a > div > span:first-child")
    ).toEqual(["Command2"]);
    expect(
        queryAllTexts(".o_command_category:nth-of-type(3) .o_command > a > div > span:first-child")
    ).toEqual(["Command3"]);

    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await runAllTimers();
    expect(".o_command").toHaveCount(4);
    expect(queryAllTexts(".o_command")).toEqual(["Command6", "Command7", "Command5", "Command4"]);
    expect(".o_command_category").toHaveCount(3);
    expect(
        queryAllTexts(".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child")
    ).toEqual(["Command6", "Command7"]);
    expect(
        queryAllTexts(".o_command_category:nth-of-type(2) .o_command > a > div > span:first-child")
    ).toEqual(["Command5"]);
    expect(
        queryAllTexts(".o_command_category:nth-of-type(3) .o_command > a > div > span:first-child")
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

    await contains(".o_command_palette_search input").edit("c", { confirm: false });
    await runAllTimers();
    expect(".o_command").toHaveCount(3);
    expect(queryAllTexts(".o_command")).toEqual(["Command1", "Command2", "Command3"]);

    expect(
        queryAllTexts(".o_command_category:nth-of-type(1) .o_command > a > div > span:first-child")
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
        // Returns the visibility of the element in the scrollable element
        const elementRect = queryOne(el).getBoundingClientRect();
        const scrollableRect = queryOne(".o_command_palette_listbox").getBoundingClientRect();
        return elementRect.bottom <= scrollableRect.bottom && elementRect.top >= scrollableRect.top;
    };

    const getFocusedCommandBorderState = () => {
        // Returns the state of the element in relation to the borders
        const elementRect = queryOne(".o_command.focused").getBoundingClientRect();
        const scrollableRect = queryOne(".o_command_palette_listbox").getBoundingClientRect();
        return {
            top: elementRect.top === scrollableRect.top,
            bottom: elementRect.bottom === scrollableRect.bottom,
        };
    };

    await animationFrame();
    // The listbox height is set to be lower than the list of commands
    // to assure the command palette is scrollable. The palette is only able to
    // display three rows of commands so we are sure we always have one row
    // element out of bounds
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
        { message: "the focus is at the top border" }
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
        { message: "the focus does not reach a border" }
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
        { message: "the focus has reached the bottom border" }
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
        { message: "the focus is still at the bottom border" }
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
        { message: "the focus does not reach a border" }
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
        { message: "the focus has reached the top border" }
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
        { message: "the focus is still at the top border" }
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    await contains(".o_command_palette_search input").edit("empty", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveText("Empty Default");
    expect(".o_command_palette_search input").toHaveAttribute("placeholder", "placeholder test");
    expect(".o_command_palette_footer").toHaveCount(1);
    expect(".o_command_palette_footer").toHaveText("My footer");

    await contains(".o_command_palette_search input").edit("", { confirm: false });
    await runAllTimers();
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Command1"]);
    expect(".o_command.focused").toHaveText(commands[0].name);
    await press("enter");
    await animationFrame();
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Command lvl2"]);

    // check that the configuration has been correctly cleaned
    await contains(".o_command_palette_search input").edit("empty", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette_listbox_empty").toHaveText("No result found");
    expect(".o_command_palette_search input").toHaveAttribute("placeholder", "Search...");
    expect(".o_command_palette_footer").toHaveCount(0);
});

test.tags("desktop")(
    "command palette dialog can be rendered and closed on outside click",
    async () => {
        await mountWithCleanup(MainComponentsContainer);

        const config = {
            providers: [],
        };
        getService("dialog").add(CommandPalette, {
            config,
        });
        await animationFrame();
        expect(".o_command_palette").toHaveCount(1);

        // Close on outside click
        await contains(getFixture()).click();
        await animationFrame();
        expect(".o_command_palette").toHaveCount(0);
    }
);

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
    expect(queryAllTexts(".o_command b")).toEqual([]);

    await contains(".o_command_palette_search input").edit("@test", { confirm: false });
    await runAllTimers();
    expect(".o_command").toHaveCount(5);
    expect(
        [...queryAll(".o_command")].map((command) => {
            return queryAllTexts(".o_command_name b", { root: command });
        })
    ).toEqual([["Test"], ["test"], ["test"], ["Test"], ["TeSt", "Test", "TEST"]]);
});

test("bold the searchValue on the commands with special char", async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command").toHaveCount(1);
    expect(queryAllTexts(".o_command")).toEqual(["Test&"]);
    expect(queryAllTexts(".o_command b")).toEqual(["&"]);
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
    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette .o_namespace").toHaveText("@");

    // remove namespace "@" because the input is empty
    await press("backspace");
    await animationFrame();
    expect(".o_command_palette .o_namespace").toHaveCount(0);
    expect(".o_command_palette_search input").toHaveValue("");

    await contains(".o_command_palette_search input").edit("@NotEmpty", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette .o_namespace").toHaveText("@");
    expect(".o_command_palette_search input").toHaveValue("NotEmpty");

    // Do not remove the namespace "@" because the input is not empty
    await press("backspace");
    await animationFrame();
    expect(".o_command_palette .o_namespace").toHaveText("@");

    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette .o_namespace").toHaveText("@");

    // Does not remove the namespace if the backspace is repeatedly applied.
    // You don't want to remove the namespace by pressing the "backspace" key
    await press("backspace", { repeat: true });
    expect(".o_command_palette .o_namespace").toHaveText("@");
});

test("generate new session id when opened", async () => {
    expect.assertions(4);

    let lastSessionId;
    CommandPalette.lastSessionId = 0;
    await mountWithCleanup(MainComponentsContainer);
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
    getService("dialog").add(CommandPalette, {
        config,
    });

    await animationFrame();
    expect(lastSessionId).toBe(0);

    await contains(".o_command_palette_search input").edit("a", { confirm: false });
    await runAllTimers();
    expect(lastSessionId).toBe(0);

    await contains(getFixture()).click();
    await animationFrame();
    expect(lastSessionId).toBe(0);

    getService("dialog").add(CommandPalette, {
        config,
    });
    await animationFrame();
    expect(lastSessionId).toBe(1);
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
    patchWithCleanup(window, {
        open: (href) => {
            expect.step(href.toString());
        },
    });
    await animationFrame();
    await contains(".o_command_palette_search input").edit("@", { confirm: false });
    await runAllTimers();
    // Check that command has link inside it
    expect(".o_command_palette .o_command:eq(0) a").toHaveAttribute("href", "https://www.odoo.com");
    // Check that we get url when doing ctrl+enter on a command having a link inside it
    await press("control+enter");
    await animationFrame();
    expect.verifySteps(["https://www.odoo.com"]);
    // Check that command has no link inside it
    expect(".o_command_palette .o_command:eq(1) a").not.toHaveAttribute("href");
    // Check that clicking on a command having a link inside it triggers the command action
    // instead of redirecting to the href (last step because it closes the command palette).
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

    await contains(".o_command_palette_search input").edit("abc", { confirm: false });
    expect(".o_command_palette_search input").toHaveValue("abc");

    await contains(".o_command_palette_search input").edit("deb", { confirm: false });
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
    expect(".o_command_palette_search i.fa.fa-spinner").toHaveCount(0);
    await contains(".o_command_palette_search input").edit("? blabla", { confirm: false });
    await runAllTimers();
    expect(".o_command_palette_search i.oi.oi-search").toHaveCount(0);
    expect(".o_command_palette_search i.fa.fa-spinner").toHaveCount(1);
    provideDef.resolve();
    await animationFrame();
    expect(".o_command_palette_search i.oi.oi-search").toHaveCount(1);
    expect(".o_command_palette_search i.fa.fa-spinner").toHaveCount(0);
});
