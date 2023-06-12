/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    getFixture,
    patchWithCleanup,
    mount,
    nextTick,
    editInput,
} from "@web/../tests/helpers/utils";

import { Component, useState, xml } from "@odoo/owl";
import { CodeEditor } from "@web/core/code_editor/code_editor";

QUnit.module("Web Components", (hooks) => {
    QUnit.module("Code Editor");

    let env;
    let target;

    hooks.beforeEach(async () => {
        env = await makeTestEnv();
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => Promise.resolve().then(fn),
        });
    });

    function getDomValue() {
        const lines = [...target.querySelectorAll(".ace_line")];
        return lines
            .map((line) => {
                const spans = [...line.querySelectorAll(":scope > span")];
                return spans.map((span) => span.textContent).join("");
            })
            .join("\n");
    }

    async function edit(value) {
        const textArea = target.querySelector(".ace_editor textarea");
        await editInput(textArea, null, value);
        return null;
    }

    function getFakeAceEditor() {
        return {
            session: {
                on: () => {},
                setMode: () => {},
                setUseWorker: () => {},
                setOptions: () => {},
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
        };
    }

    QUnit.test("Can be rendered", async (assert) => {
        class Parent extends Component {
            static components = { CodeEditor };
            static template = xml`<CodeEditor mode="'xml'" />`;
        }
        await mount(Parent, target, { env });
        assert.containsOnce(target, ".ace_editor", "Code editor is rendered");
    });

    QUnit.test("onChange props called when code is edited", async (assert) => {
        class Parent extends Component {
            static components = { CodeEditor };
            static template = xml`<CodeEditor onChange.bind="onChange" />`;
            onChange(value) {
                assert.step(value);
            }
        }

        await mount(Parent, target, { env });
        await edit("Some Text");
        assert.verifySteps(["Some Text"], "Value properly given to onChange");
    });

    QUnit.test("Default value correctly set and updates", async (assert) => {
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
            setup() {
                this.state = useState({ value: textA });
            }
            onChange(value) {
                // Changing the value of the textarea manualy triggers an Ace "remove" event
                // of the whole text (the value is thus empty), then an "add" event with the
                // actual value, this isn't ideal but we ignore the remove.
                if (value.length <= 0) {
                    return;
                }
                assert.step(value);
            }
            changeValue(newValue) {
                this.state.value = newValue;
            }
        }

        const codeEditor = await mount(Parent, target, { env });
        await nextTick();
        assert.equal(getDomValue(), textA, "Default value correctly set");

        await edit(textB);
        assert.equal(
            getDomValue(),
            textB,
            "When the textarea is updated the value is correctly changed in the dom"
        );

        codeEditor.changeValue(textC);
        await nextTick();
        await nextTick();
        assert.equal(
            getDomValue(),
            textC,
            "When the props is updated the value is correctly changed in the dom"
        );

        assert.verifySteps([textB, textC], "Changes properly given to onChange");
    });

    QUnit.test("Mode props update imports the mode", async (assert) => {
        const fakeAceEditor = getFakeAceEditor();
        fakeAceEditor.session.setMode = (mode) => {
            assert.step(mode);
        };

        patchWithCleanup(window.ace, {
            edit: () => fakeAceEditor,
        });

        class Parent extends Component {
            static components = { CodeEditor };
            static template = xml`<CodeEditor mode="state.mode" />`;
            setup() {
                this.state = useState({ mode: "xml" });
            }
            setMode(newMode) {
                this.state.mode = newMode;
            }
        }

        const codeEditor = await mount(Parent, target, { env });
        assert.verifySteps(["ace/mode/xml"], "XML mode should be loaded");

        await codeEditor.setMode("js");
        await nextTick();
        assert.verifySteps(["ace/mode/js"], "JS mode should be loaded");
    });

    QUnit.test("Theme props updates imports the theme", async (assert) => {
        const fakeAceEditor = getFakeAceEditor();
        fakeAceEditor.setTheme = (theme) => {
            assert.step(theme ? theme : "default");
        };

        patchWithCleanup(window.ace, {
            edit: () => fakeAceEditor,
        });

        class Parent extends Component {
            static components = { CodeEditor };
            static template = xml`<CodeEditor theme="state.theme" />`;
            setup() {
                this.state = useState({ theme: "" });
            }
            setTheme(newTheme) {
                this.state.theme = newTheme;
            }
        }

        const codeEditor = await mount(Parent, target, { env });
        assert.verifySteps(["default"], "Default theme should be loaded");

        await codeEditor.setTheme("monokai");
        await nextTick();
        assert.verifySteps(["ace/theme/monokai"], "Monokai theme should be loaded");
    });
});
