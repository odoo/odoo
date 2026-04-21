import { animationFrame, expect, queryAll, queryAllTexts, queryOne, test } from "@odoo/hoot";
import { Component, markup, props, proxy, signal, xml } from "@odoo/owl";
import {
    contains,
    editAce,
    mountWithCleanup,
    patchWithCleanup,
    preloadBundle,
    preventResizeObserverError,
} from "@web/../tests/web_test_helpers";

import { CodeEditor } from "@web/core/code_editor/code_editor";
import { pick } from "@web/core/utils/objects";
import { debounce } from "@web/core/utils/timing";

preloadBundle("web.ace_lib");
preventResizeObserverError();

function getDomValue() {
    return queryAll(".ace_line")
        .map((root) => queryAllTexts(`:scope > span`, { root }).join(""))
        .join("\n");
}

/*
A custom implementation to dispatch keyboard events for ace specifically
It is very naive and simple, and could extended

FIXME: Specificities of Ace 1.32.3
-- Ace heavily relies on KeyboardEvent.keyCode, so hoot's helpers
    cannot be used for this simple test.
-- Ace still relies on the keypress event
-- The textarea has no size in ace, it is a "hidden" input and a part of Ace's internals
    hoot's helpers won't focus it naturally
-- The same Ace considers that if "Win" is not part of the useragent's string, we are in a MAC environment
    So, instead of patching the useragent, we send to ace what it wants. (ie: Command + metaKey: true)
*/
function dispatchKeyboardEvents(el, tupleArray) {
    for (const [evType, eventInit] of tupleArray) {
        el.dispatchEvent(new KeyboardEvent(evType, { ...eventInit, bubbles: true }));
    }
}

test("Can be rendered", async () => {
    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor maxLines="10" mode="'xml'" />`;
    }
    await mountWithCleanup(Parent);
    expect(".ace_editor").toHaveCount(1);
});

test("CodeEditor shouldn't accept markup values", async () => {
    expect.errors(1);

    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor value="this.props.value" />`;

        props = props();
    }
    class GrandParent extends Component {
        static components = { Parent };
        static template = xml`<Parent value="this.value()"/>`;

        value = signal(`<div>Some Text</div>`);
    }

    const grandParent = await mountWithCleanup(GrandParent);
    const textMarkup = markup`<div>Some Text</div>`;

    grandParent.value.set(textMarkup);
    await animationFrame();

    expect.verifyErrors(["value is not a string"]);
});

test("onChange props called when code is edited", async () => {
    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor maxLines="10" onChange.bind="this.onChange" />`;

        onChange(value) {
            expect.step(value);
        }
    }

    await mountWithCleanup(Parent);
    await editAce("Some Text");
    expect.verifySteps(["Some Text"]);
});

test("onChange props not called when value props is updated", async () => {
    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`
            <CodeEditor
                value="this.value()"
                maxLines="10"
                onChange.bind="this.onChange"
            />
        `;

        value = signal("initial value");

        onChange(value) {
            expect.step(value);
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect(".ace_line").toHaveText("initial value");

    parent.value.set("new value");
    await animationFrame();
    await animationFrame();
    expect(".ace_line").toHaveText("new value");

    expect.verifySteps([]);
});

test("Default value correctly set and updates", async () => {
    const textA = "<div>\n<p>A Paragraph</p>\n</div>";
    const textB = "<div>\n<p>An Other Paragraph</p>\n</div>";
    const textC = "<div>\n<p>A Paragraph</p>\n</div>\n<p>And More</p>";

    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`
            <CodeEditor
                mode="'xml'"
                value="this.value()"
                onChange.bind="this.onChange"
                maxLines="200"
            />
        `;

        onChange = debounce(this._onChange.bind(this));
        value = signal(textA);

        _onChange(value) {
            // Changing the value of the textarea manualy triggers an Ace "remove" event
            // of the whole text (the value is thus empty), then an "add" event with the
            // actual value, this isn't ideal but we ignore the remove.
            if (value.length <= 0) {
                return;
            }
            expect.step(value);
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect(getDomValue()).toBe(textA);

    // Disable XML autocompletion for xml end tag.
    // Necessary because the contains().edit() helpers triggers as if it was
    // a real user interaction.
    const ace_editor = window.ace.edit(queryOne(".ace_editor"));
    ace_editor.setBehavioursEnabled(false);

    const aceEditor = window.ace.edit(queryOne(".ace_editor"));
    aceEditor.selectAll();
    await editAce(textB);
    expect(getDomValue()).toBe(textB);

    parent.value.set(textC);
    await animationFrame();
    await animationFrame();
    expect(getDomValue()).toBe(textC);
    expect.verifySteps([textB]);
});

test("Mode props update imports the mode", async () => {
    patchWithCleanup(window.ace.EditSession.prototype, {
        setMode(mode) {
            // Called once with 'undefined' at startup
            if (mode) {
                expect.step(mode);
            }
            return super.setMode(...arguments);
        },
    });

    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor maxLines="10" mode="this.mode()" />`;

        mode = signal("xml");
    }

    const parent = await mountWithCleanup(Parent);
    expect.verifySteps([{ path: "ace/mode/xml" }]);

    parent.mode.set("javascript");
    await animationFrame();

    expect.verifySteps([{ path: "ace/mode/javascript" }]);
});

test("Theme props updates imports the theme", async () => {
    patchWithCleanup(window.ace.Editor.prototype, {
        setTheme(theme) {
            expect.step(theme ? theme : "default");
            return super.setTheme(...arguments);
        },
    });

    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor maxLines="10" theme="this.theme()" />`;

        theme = signal("");
    }

    const parent = await mountWithCleanup(Parent);
    expect.verifySteps(["default"]);

    parent.theme.set("monokai");
    await animationFrame();

    expect.verifySteps(["ace/theme/monokai"]);
});

test("initial value cannot be undone", async () => {
    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor mode="'xml'" value="'some value'" class="'h-100'" />`;
    }
    await mountWithCleanup(Parent);
    await animationFrame();
    expect(".ace_editor").toHaveCount(1);
    expect(".ace_editor .ace_content").toHaveText("some value");

    const editor = window.ace.edit(queryOne(".ace_editor"));
    const undo = editor.session.$undoManager.undo.bind(editor.session.$undoManager);
    editor.session.$undoManager.undo = (...args) => {
        expect.step("ace undo");
        return undo(...args);
    };

    const aceContent = queryOne(".ace_editor textarea");
    dispatchKeyboardEvents(aceContent, [
        ["keydown", { key: "Control", keyCode: 17 }],
        ["keypress", { key: "Control", keyCode: 17 }],
        ["keydown", { key: "z", keyCode: 90, ctrlKey: true }],
        ["keypress", { key: "z", keyCode: 90, ctrlKey: true }],
        ["keyup", { key: "z", keyCode: 90, ctrlKey: true }],
        ["keyup", { key: "Control", keyCode: 17 }],
    ]);
    await animationFrame();
    expect(".ace_editor .ace_content").toHaveText("some value");
    expect.verifySteps(["ace undo"]);
});

test("code editor can take an initial cursor position", async () => {
    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor maxLines="2" value="this.value" initialCursorPosition="this.initialPosition" onChange="this.onChange"/>`;

        setup() {
            this.value = `
            1
            2
            3
            4aa
            5
            `.replace(/^\s*/gm, ""); // simple dedent

            this.initialPosition = { row: 3, column: 2 };
        }

        onChange(value, startPosition) {
            expect.step({ value, startPosition });
        }
    }
    await mountWithCleanup(Parent);
    await animationFrame();

    const editor = window.ace.edit(queryOne(".ace_editor"));
    expect(document.activeElement).toBe(editor.textInput.getElement());
    expect(editor.getCursorPosition()).toEqual({ row: 3, column: 2 });

    expect(queryAllTexts(".ace_gutter-cell")).toEqual(["3", "4", "5"]);
    expect.verifySteps([]);
    await contains(".ace_editor textarea", { displayed: true, visible: false }).edit("new\nvalue", {
        instantly: true,
    });
    expect.verifySteps([
        {
            startPosition: {
                column: 0,
                row: 0,
            },
            value: "",
        },
        {
            startPosition: {
                column: 0,
                row: 0,
            },
            value: "new\nvalue",
        },
    ]);
});

test("qweb mode readonly attributes", async () => {
    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`
            <CodeEditor
                maxLines="10"
                mode="this.props.state.mode"
                value="this.props.state.value"
                modeOptions="this.props.state.modeOptions"
                initialCursorPosition="this.props.state.initialCursorPosition"
            />
        `;

        props = props();
    }

    const initialValue = `
        <form lock-id="0" name="some_name" >
        <div />
        </form>
        `.replace(/^\s*/gm, ""); // simple dedent;

    const state = proxy({
        value: initialValue,
        mode: "qweb",
        modeOptions: {
            highlightRulesConfig: {
                readonlyAttributes: ["lock-id"],
            },
        },
        initialCursorPosition: { column: 17, row: 0 },
    });

    await mountWithCleanup(Parent, {
        props: { state },
    });
    await animationFrame();
    const editor = window.ace.edit(queryOne(".ace_editor"));
    expect(document.activeElement).toBe(editor.textInput.getElement());

    expect(".ace_editor .ace_odoo_attr_readonly").toHaveCount(5);

    for (let i = 0; i < 'lock-id="0"'.length; i++) {
        editor.commands.commands.backspace.exec(editor);
    }
    await animationFrame();
    expect(editor.getValue()).toBe(initialValue);
    expect(pick(editor.getSelection().getRange(), "start", "end")).toEqual({
        start: {
            row: 0,
            column: 6,
        },
        end: {
            row: 0,
            column: 6,
        },
    });

    editor.commands.commands.insertstring.exec(editor, 'lol="5"');
    expect(editor.getValue()).toBe(
        `
        <form lol="5" lock-id="0" name="some_name" >
        <div />
        </form>
        `.replace(/^\s*/gm, "")
    );

    editor.getSelection().selectLine();
    editor.commands.commands.backspace.exec(editor);
    expect(editor.getValue()).toBe(
        `
        <div />
        </form>
        `.replace(/^\s*/gm, "")
    );
});
