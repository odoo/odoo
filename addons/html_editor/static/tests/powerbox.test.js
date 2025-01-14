import { Plugin } from "@html_editor/plugin";
import { CORE_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    hover,
    manuallyDispatchProgrammaticEvent,
    press,
    queryAllTexts,
    scroll,
    waitFor,
} from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import {
    applyConcurrentActions,
    mergePeersSteps,
    renderTextualSelection,
    setupMultiEditor,
    validateContent,
} from "./_helpers/collaboration";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { insertText, redo, undo } from "./_helpers/user_actions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PowerboxPlugin } from "@html_editor/main/powerbox/powerbox_plugin";
import { SearchPowerboxPlugin } from "@html_editor/main/powerbox/search_powerbox_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { execCommand } from "./_helpers/userCommands";

function commandNames() {
    return queryAllTexts(".o-we-command-name");
}

test("should open the Powerbox on type `/`", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    expect(".o-we-powerbox").toHaveCount(0);
    expect(getContent(el)).toBe("<p>ab[]</p>");
    await insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
});

test.tags("iframe");
test("in iframe: should open the Powerbox on type `/`", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>", { props: { iframe: true } });
    expect("iframe").toHaveCount(1);
    expect(".o-we-powerbox").toHaveCount(0);
    expect(getContent(el)).toBe("<p>ab[]</p>");
    await insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
});

test("should correctly hint in iframes", async () => {
    const { el } = await setupEditor("<p>[]<br></p>", { props: { iframe: true } });
    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("should open the Powerbox on type `/`, but in an empty paragraph", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>");
    expect(".o-we-powerbox").toHaveCount(0);
    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
    await press("/");
    await insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
});

describe("search", () => {
    test("should filter the Powerbox contents with term", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/");
        await animationFrame();
        expect(commandNames(el).length).toBe(28);
        await insertText(editor, "head");
        await animationFrame();
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    });

    test("should hide categories when you have a search term", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/");
        await animationFrame();
        expect(commandNames(el).length).toBe(28);
        expect(".o-we-category").toHaveCount(8);
        expect(queryAllTexts(".o-we-category")).toEqual([
            "STRUCTURE",
            "BANNER",
            "FORMAT",
            "MEDIA",
            "NAVIGATION",
            "WIDGET",
            "AI TOOLS",
            "BASIC BLOC",
        ]);

        await insertText(editor, "h");
        await animationFrame();
        expect(commandNames(el).length).toBe(9);
        expect(".o-we-category").toHaveCount(0);
    });

    test.tags("iframe");
    test("should filter the Powerbox contents with term, in iframe", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>", { props: { iframe: true } });
        await insertText(editor, "/");
        await animationFrame();
        expect(commandNames(el).length).toBe(28);
        await insertText(editor, "head");
        await animationFrame();
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    });

    test("press 'backspace' should adapt adapt the search in the Powerbox", async () => {
        class TestPlugin extends Plugin {
            static id = "test";
            resources = {
                user_commands: { id: "testCommand", run: () => {} },
                powerbox_categories: { id: "test", name: "Test" },
                powerbox_items: [
                    {
                        title: "Test1",
                        description: "Test1",
                        categoryId: "test",
                        commandId: "testCommand",
                    },
                    {
                        title: "Test12",
                        description: "Test12",
                        categoryId: "test",
                        commandId: "testCommand",
                    },
                ],
            };
        }
        const { editor, el } = await setupEditor(`<p>[]</p>`, {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        expect(".o-we-powerbox").toHaveCount(0);
        await insertText(editor, "/test12");
        await animationFrame();
        expect(getContent(el)).toBe("<p>/test12[]</p>");
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el)).toEqual(["Test12"]);
        expect(".active .o-we-command-name").toHaveText("Test12");

        await press("backspace");
        await animationFrame();
        expect(getContent(el)).toBe("<p>/test1[]</p>");
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el)).toEqual(["Test1", "Test12"]);
        expect(".active .o-we-command-name").toHaveText("Test1");
    });

    test("should filter the Powerbox contents with term, even after delete backward", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el).length).toBe(28);

        await insertText(editor, "headx");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);

        await press("Backspace");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    });

    test("when the powerbox opens, the first command is selected by default", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText(commandNames(el)[0]);

        await insertText(editor, "head");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText(commandNames(el)[0]); // "Heading 1"

        await insertText(editor, "/");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText(commandNames(el)[0]);
    });

    test("should filter the Powerbox contents with term, even after a second search and delete backward", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/head");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
        expect(".active .o-we-command-name").toHaveText("Heading 1");

        await insertText(editor, "/headx");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);

        await press("backspace");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
        expect(".active .o-we-command-name").toHaveText("Heading 1");
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    });

    test("should not filter the powerbox contents when collaborator type on two different blocks", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>a[c1}{c1]b</p><p>c[c2}{c2]d</p>",
        });

        applyConcurrentActions(peerInfos, {
            c1: async (editor) => {
                await insertText(editor, "/heading");
            },
        });
        await animationFrame();
        mergePeersSteps(peerInfos);
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames()).toEqual(["Heading 1", "Heading 2", "Heading 3"]);

        applyConcurrentActions(peerInfos, {
            c2: async (editor) => {
                await insertText(editor, "g");
            },
        });
        await animationFrame();
        mergePeersSteps(peerInfos);
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames()).toEqual(["Heading 1", "Heading 2", "Heading 3"]);

        applyConcurrentActions(peerInfos, {
            c1: async (editor) => {
                await insertText(editor, "1");
            },
        });
        await animationFrame();
        mergePeersSteps(peerInfos);
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames()).toEqual(["Heading 1"]);

        renderTextualSelection(peerInfos);
        validateContent(peerInfos, "<p>a/heading1[c1}{c1]b</p><p>cg[c2}{c2]d</p>");
    });

    test("powerbox doesn't need to be displayed to apply a command (fast search)", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/head");
        expect(".o-we-powerbox").toHaveCount(0);

        await press("enter");
        expect(".o-we-powerbox").toHaveCount(0);
        expect(getContent(el)).toBe("<h1>ab[]</h1>");
    });

    describe("search keywords", () => {
        test("should search commands by optional keywords", async () => {
            class TestPlugin extends Plugin {
                static id = "test";
                resources = {
                    user_commands: { id: "testCommand", run: () => {} },
                    powerbox_categories: { id: "test", name: "Test" },
                    powerbox_items: [
                        {
                            title: "Test1",
                            description: "Test1",
                            categoryId: "test",
                            commandId: "testCommand",
                            keywords: ["apple", "orange"],
                        },
                        {
                            title: "Test2",
                            description: "Test2 has apples and oranges in its description",
                            categoryId: "test",
                            commandId: "testCommand",
                        },
                    ],
                };
            }
            const { editor, el } = await setupEditor(`<p>[]</p>`, {
                config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
            });
            expect(".o-we-powerbox").toHaveCount(0);
            insertText(editor, "/apple");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            // Both commands should be found with the keyword "apple", being the first
            // one with a higher score
            expect(commandNames(el)).toEqual(["Test1", "Test2"]);

            // Replace "apple" by "orange"
            for (let i = 0; i < 5; i++) {
                press("backspace");
            }
            insertText(editor, "/orange");
            await animationFrame();
            // Same as above
            expect(commandNames(el)).toEqual(["Test1", "Test2"]);

            insertText(editor, "s");
            // "/oranges"
            await animationFrame();
            // It no longer matches anything in the Test1 command
            expect(commandNames(el)).toEqual(["Test2"]);
        });

        test("match order: full match on keyword should come before partial matches on names or descriptions", async () => {
            class TestPlugin extends Plugin {
                static id = "test";
                resources = {
                    user_commands: { id: "testCommand", run: () => {} },
                    powerbox_categories: { id: "test", name: "Test" },
                    powerbox_items: [
                        {
                            title: "Change direction", // "icon" fuzzy matches this
                            description: "test",
                            categoryId: "test",
                            commandId: "testCommand",
                        },
                        {
                            title: "Some command",
                            description: "add a big section", // "icon" fuzzy matches this
                            categoryId: "test",
                            commandId: "testCommand",
                        },
                        {
                            title: "Insert a pictogram",
                            description: "test",
                            categoryId: "test",
                            commandId: "testCommand",
                            keywords: ["icon"],
                        },
                    ],
                };
            }
            const { editor, el } = await setupEditor(`<p>[]</p>`, {
                config: {
                    Plugins: [...CORE_PLUGINS, PowerboxPlugin, SearchPowerboxPlugin, TestPlugin],
                },
            });
            expect(".o-we-powerbox").toHaveCount(0);
            insertText(editor, "/icon");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);

            const matchedCommands = commandNames(el);
            // All three commands are found, as they all match "icon" in some way.
            expect(matchedCommands).toInclude("Change direction");
            expect(matchedCommands).toInclude("Some command");
            expect(matchedCommands).toInclude("Insert a pictogram");

            // The one with the exact keyword match should come first.
            expect(matchedCommands[0]).toBe("Insert a pictogram");
        });
    });

    describe("close", () => {
        test("should close powerbox if there is no result", async () => {
            const { el, editor } = await setupEditor("<p>a[]</p>");
            await insertText(editor, "/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            await insertText(editor, "zxzxzxz");
            await animationFrame();
            expect(getContent(el)).toBe("<p>a/zxzxzxz[]</p>");
            expect(".o-we-powerbox").toHaveCount(0);
        });
        test("should close powerbox typing a space", async () => {
            const { el, editor } = await setupEditor("<p>a[]</p>");
            await insertText(editor, "/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            // We need to add another character (b) otherwise the space will be
            // considered invisible in the getContent(el). This is a limitation
            // of the test suite that does not transform the space into a nbsp.
            await insertText(editor, " b");
            await animationFrame();
            expect(getContent(el)).toBe("<p>a/ b[]</p>");
            expect(".o-we-powerbox").toHaveCount(0);
        });

        test("delete '/' should close the powerbox", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            await insertText(editor, "/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            expect(getContent(el)).toBe("<p>/[]</p>");

            await press("backspace");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(0);
            expect(getContent(el)).toBe(
                `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
            );

            await insertText(editor, "a");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(0);
            expect(getContent(el)).toBe("<p>a[]<br></p>");
        });

        test("press escape should close the powerbox", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            await insertText(editor, "/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            expect(getContent(el)).toBe("<p>/[]</p>");

            await press("escape");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(0);
            expect(getContent(el)).toBe(`<p>/[]</p>`);

            await insertText(editor, "h");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(0);
            expect(getContent(el)).toBe(`<p>/h[]</p>`);
        });
    });
});

test("should execute command and remove term and hot character on Enter", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    await insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".o-we-powerbox").toHaveCount(1);
    await press("Enter");
    expect(getContent(el)).toBe("<h1>ab[]</h1>");
    expect(".o-we-powerbox").toHaveCount(1);
    // need 1 animation frame to close
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

test("should execute command and remove term and hot character on Tab", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    await insertText(editor, "/head");
    await animationFrame();
    await press("Tab");
    expect(getContent(el)).toBe("<h1>ab[]</h1>");
});

test.todo("should close the powerbox if keyup event is called on other block", async () => {
    // ged: not sure i understand the goal of this test
    const { editor } = await setupEditor("<p>ab</p><p>c[]d</p>");
    await insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    // await dispatch(editor.editable, "keyup");
    expect(".o-we-powerbox").toHaveCount(1);
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

test.tags("desktop");
test("should insert a 3x3 table on type `/table`", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    expect(getContent(el)).toBe(`<p placeholder='Type "/" for commands' class="o-we-hint">[]</p>`);

    await insertText(editor, "/table");
    await waitFor(".o-we-powerbox ");

    await press("Enter");
    await animationFrame();

    await press("Enter");
    await tick();
    expect(getContent(el)).toBe(
        `<table class="table table-bordered o_table"><tbody><tr><td><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr></tbody></table><p><br></p>`
    );
});

test.tags("mobile");
test("should insert a 3x3 table on type `/table` in mobile view", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>");
    await insertText(editor, "/table");
    await waitFor(".o-we-powerbox ");
    await press("Enter");
    await tick();
    expect(getContent(el)).toBe(
        `<table class="table table-bordered o_table"><tbody><tr><td><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr></tbody></table><p><br></p>`
    );
});

test("should toggle list on empty paragraph", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>");

    /** @todo fix warnings */
    patchWithCleanup(console, { warn: () => {} });

    await insertText(editor, "/");
    // @todo @phoenix: remove this once we manage inputs.
    // Simulate <br> removal by contenteditable when something is inserted
    el.querySelector("p > br").remove();
    await insertText(editor, "checklist");
    expect(getContent(el)).toBe("<p>/checklist[]</p>");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Checklist"]);
    expect(".o-we-powerbox").toHaveCount(1);
    await press("Enter");
    expect(getContent(el)).toBe(
        `<ul class="o_checklist"><li placeholder="List" class="o-we-hint">[]<br></li></ul>`
    );
    // need 1 animation frame to close
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

class NoOpPlugin extends Plugin {
    static id = "noOp";
    resources = {
        user_commands: [
            {
                id: "noOp",
                run: () => {},
            },
        ],
        powerbox_categories: { id: "no_op", name: "No-op" },
        powerbox_items: [
            {
                title: "No-op",
                description: "No-op",
                categoryId: "no_op",
                icon: "fa-header",
                commandId: "noOp",
            },
        ],
    };
}

test("should restore state before /command insertion when command is executed (1)", async () => {
    const { el, editor } = await setupEditor("<p>abc[]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, NoOpPlugin] },
    });
    await insertText(editor, "/no-op");
    expect(getContent(el)).toBe("<p>abc/no-op[]</p>");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    expect(commandNames(el)).toEqual(["No-op"]);
    await press("Enter");
    expect(getContent(el)).toBe("<p>abc[]</p>");
});

test("should restore state before /command insertion when command is executed (2)", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>", {
        config: { Plugins: [...MAIN_PLUGINS, NoOpPlugin] },
    });

    /** @todo fix warnings */
    patchWithCleanup(console, { warn: () => {} });

    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
    await insertText(editor, "/");
    // @todo @phoenix: remove this once we manage inputs.
    // Simulate <br> removal by contenteditable when something is inserted
    el.querySelector("p > br").remove();
    await insertText(editor, "no-op");
    expect(getContent(el)).toBe("<p>/no-op[]</p>");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    expect(commandNames(el)).toEqual(["No-op"]);
    await press("Enter");
    expect(getContent(el)).toBe(
        `<p class="o-we-hint" placeholder='Type "/" for commands'>[]<br></p>`
    );
});

test("should discard /command insertion from history when command is executed", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>");

    /** @todo fix warnings */
    patchWithCleanup(console, { warn: () => {} });

    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
    // @todo @phoenix: remove this once we manage inputs.
    // Simulate <br> removal by contenteditable when something is inserted
    el.querySelector("p > br").remove();
    await insertText(editor, "abc/heading1");
    expect(getContent(el)).toBe("<p>abc/heading1[]</p>");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    expect(commandNames(el)).toEqual(["Heading 1"]);
    await press("Enter");
    expect(getContent(el)).toBe("<h1>abc[]</h1>");
    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe("<p>abc[]</p>");
    execCommand(editor, "historyRedo");
    expect(getContent(el)).toBe("<h1>abc[]</h1>");
    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe("<p>abc[]</p>");
    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe("<p>ab[]</p>");
    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe("<p>a[]</p>");
    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe(
        `<p class="o-we-hint" placeholder='Type "/" for commands'>[]<br></p>`
    );
});

test("should adapt the search of the powerbox when undo/redo", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");
    await insertText(editor, "/heading1");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1"]);

    undo(editor);
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);

    redo(editor);
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1"]);
});

test("should open the Powerbox on type `/` in DIV", async () => {
    const { editor } = await setupEditor(`<div>ab<br><br>[]</div>`);
    expect(".o-we-powerbox").toHaveCount(0);
    await insertText(editor, "/");
    await animationFrame();

    expect(".o-we-powerbox").toHaveCount(1);
});

test("press 'arrowdown' to navigate", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");
    await insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".active .o-we-command-name").toHaveText("Heading 1");

    await press("arrowdown");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 2");

    await press("arrowdown");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 3");

    await press("arrowdown");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 1");
});

test("press 'arrowup' to navigate", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");
    await insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".active .o-we-command-name").toHaveText("Heading 1");

    await press("arrowup");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 3");

    await press("arrowup");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 2");

    await press("arrowup");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 1");
});

test("press 'arrowleft' should close PowerBox", async () => {
    const { editor } = await setupEditor("<p>ab[]c</p>");
    await insertText(editor, "/head");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);

    await press("arrowleft");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

test("press 'arrowright' should close PowerBox", async () => {
    const { editor } = await setupEditor("<p>ab[]c</p>");
    await insertText(editor, "/head");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);

    await press("arrowright");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

test.tags("desktop");
test("select command with 'mouseenter'", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");

    // Hoot don't trigger a mousemove event at the start of an hover, if we don't hover
    // another element before. So we need to do a first hover to set a previous element.
    await hover(".odoo-editor-editable");

    await insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".active .o-we-command-name").toHaveText("Heading 1");

    await hover(".o-we-command-name:last");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 3");

    await press("enter");
    expect(getContent(el)).toBe("<h3>ab[]</h3>");
});

test.tags("desktop");
test("select command with 'mouseenter' after scroll -- doc in iframe", async () => {
    const { editor } = await setupEditor("<p>ab[]</p>", { props: { iframe: true } });

    // Hoot don't trigger a mousemove event at the start of an hover, if we don't hover
    // another element before. So we need to do a first hover to set a previous element.
    await hover("body"); // Hover on main document's body

    await insertText(editor, "/");
    await animationFrame();

    await hover(".o-we-command-name:eq(1)");
    await scroll(".o-we-powerbox", { y: 1000 }); // Scroll to bottom
    await animationFrame();
    await scroll(".o-we-powerbox", { y: 0 }); // Scroll back to top

    await hover(".o-we-command-name:eq(3)");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("4 columns");
});

test("click on a command", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");
    await insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".active .o-we-command-name").toHaveText("Heading 1");

    await click(".o-we-command-name:last");
    expect(getContent(el)).toBe("<h3>ab[]</h3>");
});

test("create a new <p> with press 'Enter' then apply a powerbox command", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");
    // Event trigger when you press "Enter" => create a new paragraph
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "/head");
    await animationFrame();
    await press("Enter");
    expect(getContent(el)).toBe("<p>ab</p><h1>[]cd</h1>");
});

// @todo @phoenix Need a fix in hoot duplicate error are throw
test.todo("add plugins with the same powerboxCategory should crash", async () => {
    expect.errors(1);
    patchWithCleanup(console, {
        warn: (msg) => expect.step(msg),
    });
    class Plugin1 extends Plugin {
        resources = {
            powerbox_categories: withSequence(10, { id: "test", name: "Test" }),
        };
    }
    class Plugin2 extends Plugin {
        resources = {
            powerbox_categories: withSequence(10, { id: "test", name: "Test" }),
        };
    }
    await expect(
        setupEditor("<p>ab[]cd</p>", {
            config: { Plugins: [...MAIN_PLUGINS, Plugin1, Plugin2] },
        })
    ).rejects.toThrow();
    expect(["Duplicate category id: test"]).toVerifyErrors();
    expect([
        "[Owl] Unhandled error. Destroying the root component",
        "[Owl] Unhandled error. Destroying the root component",
        "[Owl] Unhandled error. Destroying the root component",
    ]).toVerifySteps();
});
