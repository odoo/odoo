import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, markup, useState, xml } from "@odoo/owl";
import {
    contains,
    editAce,
    mountWithCleanup,
    patchWithCleanup,
    preloadBundle,
    preventResizeObserverError,
} from "@web/../tests/web_test_helpers";

import { CodeEditor } from "@web/core/code_editor/code_editor";
import { debounce } from "@web/core/utils/timing";

preloadBundle("web.ace_lib");
preventResizeObserverError();

function getDomValue() {
    return queryAll(".ace_line")
        .map((root) => queryAllTexts(`:scope > span`, { root }).join(""))
        .join("\n");
}

function getFakeAceEditor() {
    return {
        session: {
            on: () => {},
            setMode: () => {},
            setUseWorker: () => {},
            setOptions: () => {},
            getValue: () => {},
            setValue: () => {},
        },
        renderer: {
            setOptions: () => {},
            $cursorLayer: { element: { style: {} } },
        },
        setOptions: () => {},
        setValue: () => {},
        getValue: () => "",
        setTheme: () => {},
        resize: () => {},
        destroy: () => {},
        setSession: () => {},
        getSession() {
            return this.session;
        },
        on: () => {},
    };
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
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    expect(".ace_editor").toHaveCount(1);
});

test("CodeEditor shouldn't accepts markup values", async () => {
    expect.errors(1);

    patchWithCleanup(console, {
        warn: (msg) => expect.step(msg),
    });

    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor value="props.value" />`;
        static props = ["*"];
    }
    class GrandParent extends Component {
        static components = { Parent };
        static template = xml`<Parent value="state.value"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ value: `<div>Some Text</div>` });
        }
    }

    const codeEditor = await mountWithCleanup(GrandParent);
    const textMarkup = markup`<div>Some Text</div>`;

    codeEditor.state.value = textMarkup;
    await animationFrame();

    expect.verifyErrors(["Invalid props for component 'CodeEditor': 'value' is not valid"]);
    expect.verifySteps(["[Owl] Unhandled error. Destroying the root component"]);
});

test("onChange props called when code is edited", async () => {
    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor maxLines="10" onChange.bind="onChange" />`;
        static props = ["*"];
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
                value="state.value"
                maxLines="10"
                onChange.bind="onChange"
            />
        `;
        static props = ["*"];
        state = useState({ value: "initial value" });
        onChange(value) {
            expect.step(value || "__emptystring__");
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect(".ace_line").toHaveText("initial value");

    parent.state.value = "new value";
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
                value="state.value"
                onChange.bind="onChange"
                maxLines="200"
            />
        `;
        static props = ["*"];
        setup() {
            this.state = useState({ value: textA });
            this.onChange = debounce(this.onChange.bind(this));
        }
        onChange(value) {
            // Changing the value of the textarea manualy triggers an Ace "remove" event
            // of the whole text (the value is thus empty), then an "add" event with the
            // actual value, this isn't ideal but we ignore the remove.
            if (value.length <= 0) {
                return;
            }
            expect.step(value);
        }
        changeValue(newValue) {
            this.state.value = newValue;
        }
    }

    const codeEditor = await mountWithCleanup(Parent);
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

    codeEditor.changeValue(textC);
    await animationFrame();
    await animationFrame();
    expect(getDomValue()).toBe(textC);
    expect.verifySteps([textB]);
});

test("Mode props update imports the mode", async () => {
    const fakeAceEditor = getFakeAceEditor();
    fakeAceEditor.session.setMode = (mode) => {
        expect.step(mode);
    };

    patchWithCleanup(window.ace, {
        edit: () => fakeAceEditor,
    });

    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor maxLines="10" mode="state.mode" />`;
        static props = ["*"];
        setup() {
            this.state = useState({ mode: "xml" });
        }
        setMode(newMode) {
            this.state.mode = newMode;
        }
    }

    const codeEditor = await mountWithCleanup(Parent);
    expect.verifySteps(["ace/mode/xml"]);

    await codeEditor.setMode("javascript");
    await animationFrame();
    expect.verifySteps(["ace/mode/javascript"]);
});

test("Theme props updates imports the theme", async () => {
    const fakeAceEditor = getFakeAceEditor();
    fakeAceEditor.setTheme = (theme) => {
        expect.step(theme ? theme : "default");
    };

    patchWithCleanup(window.ace, {
        edit: () => fakeAceEditor,
    });

    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor maxLines="10" theme="state.theme" />`;
        static props = ["*"];
        setup() {
            this.state = useState({ theme: "" });
        }
        setTheme(newTheme) {
            this.state.theme = newTheme;
        }
    }

    const codeEditor = await mountWithCleanup(Parent);
    expect.verifySteps(["default"]);

    await codeEditor.setTheme("monokai");
    await animationFrame();
    expect.verifySteps(["ace/theme/monokai"]);
});

test("initial value cannot be undone", async () => {
    class Parent extends Component {
        static components = { CodeEditor };
        static template = xml`<CodeEditor mode="'xml'" value="'some value'" class="'h-100'" />`;
        static props = ["*"];
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
        static template = xml`<CodeEditor maxLines="2" value="value" initialCursorPosition="initialPosition" onChange="onChange"/>`;
        static props = ["*"];

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
