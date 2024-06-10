import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    hover,
    manuallyDispatchProgrammaticEvent,
    press,
    queryAllTexts,
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
import { waitFor } from "../../../web/static/lib/hoot-dom/hoot-dom";

function commandNames() {
    return queryAllTexts(".o-we-command-name");
}

test("should open the Powerbox on type `/`", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    expect(".o-we-powerbox").toHaveCount(0);
    expect(getContent(el)).toBe("<p>ab[]</p>");
    insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
});

test.tags("iframe")("in iframe: should open the Powerbox on type `/`", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>", { props: { iframe: true } });
    expect("iframe").toHaveCount(1);
    expect(".o-we-powerbox").toHaveCount(0);
    expect(getContent(el)).toBe("<p>ab[]</p>");
    insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
});

test("should open the Powerbox on type `/`, but in an empty paragraph", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>");
    expect(".o-we-powerbox").toHaveCount(0);
    expect(getContent(el)).toBe(
        `<p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>`
    );
    press("/");
    insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
});

describe("search", () => {
    test("should filter the Powerbox contents with term", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/");
        await animationFrame();
        expect(commandNames(el).length).toBe(17);
        insertText(editor, "head");
        await animationFrame();
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    });

    test("should hide categories when you have a search term", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/");
        await animationFrame();
        expect(commandNames(el).length).toBe(17);
        expect(".o-we-category").toHaveCount(4);
        expect(queryAllTexts(".o-we-category")).toEqual([
            "STRUCTURE",
            "MEDIA",
            "FORMAT",
            "NAVIGATION",
        ]);

        insertText(editor, "h");
        await animationFrame();
        expect(commandNames(el).length).toBe(7);
        expect(".o-we-category").toHaveCount(0);
    });

    test.tags("iframe")("should filter the Powerbox contents with term, in iframe", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>", { props: { iframe: true } });
        insertText(editor, "/");
        await animationFrame();
        expect(commandNames(el).length).toBe(17);
        insertText(editor, "head");
        await animationFrame();
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    });

    test("press 'backspace' should adapt adapt the search in the Powerbox", async () => {
        class TestPlugin extends Plugin {
            static name = "test";
            static resources = () => ({
                powerboxCategory: { id: "test", name: "Test" },
                powerboxCommands: [
                    {
                        name: "Test1",
                        description: "Test1",
                        category: "test",
                    },
                    {
                        name: "Test12",
                        description: "Test12",
                        category: "test",
                    },
                ],
            });
        }
        const { editor, el } = await setupEditor(`<p>[]</p>`, {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        expect(".o-we-powerbox").toHaveCount(0);
        insertText(editor, "/test12");
        await animationFrame();
        expect(getContent(el)).toBe("<p>/test12[]</p>");
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el)).toEqual(["Test12"]);
        expect(".active .o-we-command-name").toHaveText("Test12");

        press("backspace");
        await animationFrame();
        expect(getContent(el)).toBe("<p>/test1[]</p>");
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el)).toEqual(["Test1", "Test12"]);
        expect(".active .o-we-command-name").toHaveText("Test1");
    });

    test("should filter the Powerbox contents with term, even after delete backward", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el).length).toBe(17);

        insertText(editor, "headx");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);

        press("Backspace");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    });

    test("when the powerbox opens, the first command is selected by default", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText(commandNames(el)[0]);

        insertText(editor, "head");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText(commandNames(el)[0]); // "Heading 1"

        insertText(editor, "/");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText(commandNames(el)[0]);
    });

    test("should filter the Powerbox contents with term, even after a second search and delete backward", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/head");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
        expect(".active .o-we-command-name").toHaveText("Heading 1");

        insertText(editor, "/headx");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);

        press("backspace");
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
            c1: (editor) => {
                insertText(editor, "/heading");
            },
        });
        await animationFrame();
        mergePeersSteps(peerInfos);
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames()).toEqual(["Heading 1", "Heading 2", "Heading 3"]);

        applyConcurrentActions(peerInfos, {
            c2: (editor) => {
                insertText(editor, "g");
            },
        });
        await animationFrame();
        mergePeersSteps(peerInfos);
        expect(".o-we-powerbox").toHaveCount(1);
        expect(commandNames()).toEqual(["Heading 1", "Heading 2", "Heading 3"]);

        applyConcurrentActions(peerInfos, {
            c1: (editor) => {
                insertText(editor, "1");
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
        insertText(editor, "/head");
        expect(".o-we-powerbox").toHaveCount(0);

        press("enter");
        expect(".o-we-powerbox").toHaveCount(0);
        expect(getContent(el)).toBe("<h1>ab[]</h1>");
    });

    describe("close", () => {
        test("should close powerbox if there is no result", async () => {
            const { el, editor } = await setupEditor("<p>a[]</p>");
            insertText(editor, "/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            insertText(editor, "zxzxzxz");
            await animationFrame();
            expect(getContent(el)).toBe("<p>a/zxzxzxz[]</p>");
            expect(".o-we-powerbox").toHaveCount(0);
        });
        test("should close powerbox typing a space", async () => {
            const { el, editor } = await setupEditor("<p>a[]</p>");
            insertText(editor, "/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            // We need to add another character (b) otherwise the space will be
            // considered invisible in the getContent(el). This is a limitation
            // of the test suite that does not transform the space into a nbsp.
            insertText(editor, " b");
            await animationFrame();
            expect(getContent(el)).toBe("<p>a/ b[]</p>");
            expect(".o-we-powerbox").toHaveCount(0);
        });

        test("delete '/' should close the powerbox", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            insertText(editor, "/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            expect(getContent(el)).toBe("<p>/[]</p>");

            press("backspace");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(0);
            expect(getContent(el)).toBe(
                `<p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>`
            );

            insertText(editor, "a");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(0);
            expect(getContent(el)).toBe("<p>a[]<br></p>");
        });

        test("press escape should close the powerbox", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            insertText(editor, "/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(1);
            expect(getContent(el)).toBe("<p>/[]</p>");

            press("escape");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(0);
            expect(getContent(el)).toBe(`<p>/[]</p>`);
        });
    });
});

test("should execute command and remove term and hot character on Enter", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".o-we-powerbox").toHaveCount(1);
    press("Enter");
    expect(getContent(el)).toBe("<h1>ab[]</h1>");
    expect(".o-we-powerbox").toHaveCount(1);
    // need 1 animation frame to close
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

test("should execute command and remove term and hot character on Tab", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    insertText(editor, "/head");
    await animationFrame();
    press("Tab");
    expect(getContent(el)).toBe("<h1>ab[]</h1>");
});

test.todo("should close the powerbox if keyup event is called on other block", async () => {
    // ged: not sure i understand the goal of this test
    const { editor } = await setupEditor("<p>ab</p><p>c[]d</p>");
    insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    // await dispatch(editor.editable, "keyup");
    expect(".o-we-powerbox").toHaveCount(1);
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

test.tags("desktop")("should insert a 3x3 table on type `/table`", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    expect(getContent(el)).toBe(`<p placeholder="Type "/" for commands" class="o-we-hint">[]</p>`);

    insertText(editor, "/table");
    await waitFor(".o-we-powerbox ");

    press("Enter");
    await animationFrame();

    press("Enter");
    await tick();
    expect(getContent(el)).toBe(
        `<table class="table table-bordered o_table"><tbody><tr><td><p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr></tbody></table><p></p><br>`
    );
});

test.tags("mobile")("should insert a 3x3 table on type `/table` in mobile view", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>");
    insertText(editor, "/table");
    await waitFor(".o-we-powerbox ");
    press("Enter");
    await tick();
    expect(getContent(el)).toBe(
        `<table class="table table-bordered o_table"><tbody><tr><td><p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr></tbody></table><p><br></p>`
    );
});

test("should toggle list on empty paragraph", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>");
    insertText(editor, "/");
    // @todo @phoenix: remove this once we manage inputs.
    // Simulate <br> removal by contenteditable when something is inserted
    el.querySelector("p > br").remove();
    insertText(editor, "checklist");
    expect(getContent(el)).toBe("<p>/checklist[]</p>");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Checklist"]);
    expect(".o-we-powerbox").toHaveCount(1);
    press("Enter");
    expect(getContent(el)).toBe(
        `<ul class="o_checklist"><li placeholder="List" class="o-we-hint">[]<br></li></ul>`
    );
    // need 1 animation frame to close
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

class NoOpPlugin extends Plugin {
    static name = "no_op";
    static resources = () => ({
        powerboxCategory: { id: "no_op", name: "No-op" },
        powerboxCommands: [
            {
                name: "No-op",
                description: "No-op",
                category: "no_op",
                fontawesome: "fa-header",
                action(dispatch) {
                    dispatch("NO_OP");
                },
            },
        ],
    });
}

test("should restore state before /command insertion when command is executed (1)", async () => {
    const { el, editor } = await setupEditor("<p>abc[]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, NoOpPlugin] },
    });
    insertText(editor, "/no-op");
    expect(getContent(el)).toBe("<p>abc/no-op[]</p>");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    expect(commandNames(el)).toEqual(["No-op"]);
    press("Enter");
    expect(getContent(el)).toBe("<p>abc[]</p>");
});

test("should restore state before /command insertion when command is executed (2)", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>", {
        config: { Plugins: [...MAIN_PLUGINS, NoOpPlugin] },
    });
    expect(getContent(el)).toBe(
        `<p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>`
    );
    insertText(editor, "/");
    // @todo @phoenix: remove this once we manage inputs.
    // Simulate <br> removal by contenteditable when something is inserted
    el.querySelector("p > br").remove();
    insertText(editor, "no-op");
    expect(getContent(el)).toBe("<p>/no-op[]</p>");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    expect(commandNames(el)).toEqual(["No-op"]);
    press("Enter");
    expect(getContent(el)).toBe(
        '<p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>'
    );
});

test("should discard /command insertion from history when command is executed", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>");
    expect(getContent(el)).toBe(
        `<p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>`
    );
    // @todo @phoenix: remove this once we manage inputs.
    // Simulate <br> removal by contenteditable when something is inserted
    el.querySelector("p > br").remove();
    insertText(editor, "abc/heading1");
    expect(getContent(el)).toBe("<p>abc/heading1[]</p>");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    expect(commandNames(el)).toEqual(["Heading 1"]);
    press("Enter");
    expect(getContent(el)).toBe("<h1>abc[]</h1>");
    editor.dispatch("HISTORY_UNDO");
    expect(getContent(el)).toBe("<p>abc[]</p>");
    editor.dispatch("HISTORY_REDO");
    expect(getContent(el)).toBe("<h1>abc[]</h1>");
    editor.dispatch("HISTORY_UNDO");
    expect(getContent(el)).toBe("<p>abc[]</p>");
    editor.dispatch("HISTORY_UNDO");
    expect(getContent(el)).toBe("<p>ab[]</p>");
    editor.dispatch("HISTORY_UNDO");
    expect(getContent(el)).toBe("<p>a[]</p>");
    editor.dispatch("HISTORY_UNDO");
    expect(getContent(el)).toBe(
        `<p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>`
    );
});

test("should adapt the search of the powerbox when undo/redo", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");
    insertText(editor, "/heading1");
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
    insertText(editor, "/");
    await animationFrame();

    expect(".o-we-powerbox").toHaveCount(1);
});

test("press 'arrowdown' to navigate", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");
    insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".active .o-we-command-name").toHaveText("Heading 1");

    press("arrowdown");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 2");

    press("arrowdown");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 3");

    press("arrowdown");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 1");
});

test("press 'arrowup' to navigate", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");
    insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".active .o-we-command-name").toHaveText("Heading 1");

    press("arrowup");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 3");

    press("arrowup");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 2");

    press("arrowup");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 1");
});

test("press 'arrowleft' should close PowerBox", async () => {
    const { editor } = await setupEditor("<p>ab[]c</p>");
    insertText(editor, "/head");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);

    press("arrowleft");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

test("press 'arrowright' should close PowerBox", async () => {
    const { editor } = await setupEditor("<p>ab[]c</p>");
    insertText(editor, "/head");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);

    press("arrowright");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
});

test.tags("desktop")("select command with 'mouseenter'", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");

    // Hoot don't trigger a mousemove event at the start of an hover, if we don't hover
    // another element before. So we need to do a first hover to set a previous element.
    hover(".odoo-editor-editable");

    insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".active .o-we-command-name").toHaveText("Heading 1");

    hover(".o-we-command-name:last");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Heading 3");

    press("enter");
    expect(getContent(el)).toBe("<h3>ab[]</h3>");
});

test("click on a command", async () => {
    const { editor, el } = await setupEditor("<p>ab[]</p>");
    insertText(editor, "/head");
    await animationFrame();
    expect(commandNames(el)).toEqual(["Heading 1", "Heading 2", "Heading 3"]);
    expect(".active .o-we-command-name").toHaveText("Heading 1");

    click(".o-we-command-name:last");
    expect(getContent(el)).toBe("<h3>ab[]</h3>");
});

test("create a new <p> with press 'Enter' then apply a powerbox command", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");
    // Event trigger when you press "Enter" => create a new paragraph
    manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    insertText(editor, "/head");
    await animationFrame();
    press("Enter");
    expect(getContent(el)).toBe("<p>ab</p><h1>[]cd</h1>");
});
