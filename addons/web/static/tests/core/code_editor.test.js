import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, markup, useState, xml } from "@odoo/owl";
import {
    editAce,
    mountWithCleanup,
    patchWithCleanup,
    preventResizeObserverError,
} from "@web/../tests/web_test_helpers";

import { CodeEditor } from "@web/core/code_editor/code_editor";
import { debounce } from "@web/core/utils/timing";

preventResizeObserverError();

function getDomValue() {
    return queryAll(".ace_line")
        .map((line) => queryAllTexts(":scope > span", { root: line }).join(""))
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

    console.warn = (msg) => expect.step(msg);

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
    const textMarkup = markup("<div>Some Text</div>");

    codeEditor.state.value = textMarkup;
    await animationFrame();

    expect(["Invalid props for component 'CodeEditor': 'value' is not valid"]).toVerifyErrors();
    expect(["[Owl] Unhandled error. Destroying the root component"]).toVerifySteps();
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
    expect([
        "S",
        "So",
        "Som",
        "Some",
        "Some ",
        "Some T",
        "Some Te",
        "Some Tex",
        "Some Text",
    ]).toVerifySteps();
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

    expect([]).toVerifySteps();
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

    await editAce(textB);
    expect(getDomValue()).toBe(textB);

    codeEditor.changeValue(textC);
    await animationFrame();
    await animationFrame();
    expect(getDomValue()).toBe(textC);
    expect([textB]).toVerifySteps();
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
    expect(["ace/mode/xml"]).toVerifySteps();

    await codeEditor.setMode("javascript");
    await animationFrame();
    expect(["ace/mode/javascript"]).toVerifySteps();
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
    expect(["default"]).toVerifySteps({ message: "Default theme should be loaded" });

    await codeEditor.setTheme("monokai");
    await animationFrame();
    expect(["ace/theme/monokai"]).toVerifySteps({ message: "Monokai theme should be loaded" });
});
