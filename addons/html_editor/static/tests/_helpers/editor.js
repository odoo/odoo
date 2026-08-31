import "./html_editor_mock_server.js";

import { EmbeddedComponentPlugin } from "@html_editor/others/embedded_component_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { fixInvalidHTML } from "@html_editor/utils/sanitize";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { destroy, expect, getFixture } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame, Deferred, tick } from "@odoo/hoot-mock";
import { Component, markup, onWillDestroy, xml } from "@odoo/owl";
import { toExplicitString } from "@web/../lib/hoot/hoot_utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { dispatchCleanForSave } from "./dispatch.js";
import { getContent, getSelection, setContent } from "./selection.js";

export const Direction = {
    BACKWARD: "BACKWARD",
    FORWARD: "FORWARD",
};

const defaultTestConfig = {
    debouncePowerbuttons: false,
    debounceHints: false,
};

// The contrast plugin rewrites every colour it finds the moment the editor
// starts, which would move the goalposts under every colour assertion in this
// suite. Tests that want it ask for it: `config: { Plugins: [...MAIN_PLUGINS] }`.
export const PLUGINS_TO_EXCLUDE = ["contrast"];
export const TEST_PLUGINS = MAIN_PLUGINS.filter((p) => !PLUGINS_TO_EXCLUDE.includes(p.id));

export const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

class TestEditor extends Component {
    static template = xml`
        <t t-if="props.styleContent">
            <style t-esc="props.styleContent"></style>
        </t>
        <Wysiwyg t-props="wysiwygProps" />`;
    static components = { Wysiwyg };
    static props = [
        "wysiwygProps",
        "content",
        "styleContent?",
        "onMounted?",
        "onWillDestroy?",
    ];

    setup() {
        const props = this.props;
        const content = fixInvalidHTML(props.content);
        this.wysiwygProps = Object.assign({}, this.props.wysiwygProps);
        const iframe = this.props.wysiwygProps.iframe;
        const oldOnLoad = this.wysiwygProps.onLoad;
        this.wysiwygProps.onLoad = function (editor) {
            const oldAttach = editor.attachTo;
            editor.attachTo = function (el) {
                if (iframe) {
                    const html = `<div>${content || ""}</div><style>${props.styleContent}</style>`;
                    el.innerHTML = html;
                    el = el.firstChild;
                }
                if (content) {
                    el.setAttribute("contenteditable", true);
                    const configSelection = getSelection(el, content);
                    if (configSelection) {
                        el.focus();
                    }
                    if (props.onMounted) {
                        props.onMounted(el);
                    } else {
                        setContent(el, content);
                    }
                }
                oldAttach.call(this, el);
            };
            oldOnLoad.call(this, editor);
        };
        if (this.props.onWillDestroy) {
            onWillDestroy(this.props.onWillDestroy);
        }
        if (this.wysiwygProps.config.Plugins?.includes(EmbeddedComponentPlugin)) {
            this.wysiwygProps.config.embeddedComponentInfo = {
                app: this.__owl__.app,
                env: this.env,
            };
        }
    }
}

/**
 * @typedef { Object } TestConfig
 * @property { import("@html_editor/editor").EditorConfig } [config]
 * @property { string } [styleContent]
 * @property { Function } [onMounted]
 * @property { Object } [props]
 * @property { boolean } [toolbar]
 * @property { Object } [env]
 */

/**
 * @typedef { import("@html_editor/plugin").Plugin } Plugin
 * @typedef { import("@html_editor/editor").Editor } Editor
 */

/**
 * @param { string } content
 * @param {TestConfig} [options]
 * @returns { Promise<{el: HTMLElement; editor: Editor; plugins: Map<string,Plugin>}> }
 */
export async function setupEditor(content, options = {}) {
    const wysiwygProps = Object.assign({}, options.props);
    wysiwygProps.config = {
        Plugins: TEST_PLUGINS,
        ...defaultTestConfig,
        ...(options.config || {}),
    };
    const attachedEditor = new Promise((resolve) => {
        wysiwygProps.onLoad = (editor) => {
            const oldAttachTo = editor.attachTo;
            editor.attachTo = function (el) {
                oldAttachTo.call(this, el);
                resolve(editor);
            };
        };
    });
    const styleContent = options.styleContent || "";
    const editorComponent = await mountWithCleanup(TestEditor, {
        props: {
            content: markup(content),
            wysiwygProps,
            styleContent,
            onMounted: options.onMounted,
            onWillDestroy: options.onWillDestroy,
        },
        env: options.env,
    });

    const editor = await attachedEditor;
    const plugins = new Map(
        editor.plugins.map((plugin) => [plugin.constructor.id, plugin]),
    );
    if (plugins.get("embeddedComponents")) {
        await animationFrame();
    }

    return {
        el: editor.editable,
        editor,
        plugins,
        editorComponent,
    };
}

/**
 * @typedef { Object } TestEditorConfig
 * @property { string } contentBefore
 * @property { string } [contentBeforeEdit]
 * @property { (editor: Editor) => any } [stepFunction]
 * @property { string } [contentAfter]
 * @property { string } [contentAfterEdit]
 * @property { (content: string, expected: string, phase: string, editor: Editor) => Promise<void> } [compareFunction]
 */

/**
 * @param {TestEditorConfig & TestConfig} config
 */
export async function testEditor(config) {
    let {
        contentBefore,
        contentBeforeEdit,
        stepFunction,
        contentAfter,
        contentAfterEdit,
        compareFunction,
    } = config;
    if (!compareFunction) {
        compareFunction = (content, expected, phase) => {
            expect(content).toBe(expected, {
                message: `(testEditor) ${phase} should be strictly equal to ${toExplicitString(
                    expected,
                )}`,
            });
        };
    }
    delete config.props?.mobile;
    const willBeDestroyed = new Deferred();
    config.onWillDestroy = () => willBeDestroyed.resolve();
    const { el, editor, editorComponent } = await setupEditor(contentBefore, config);
    editor.shared.history.stageSelection();

    if (config.props?.iframe) {
        expect(".o-wysiwyg iframe").toHaveCount(1);
    }

    await tick();

    if (contentBeforeEdit) {
        await compareFunction(
            getContent(el, config.options),
            contentBeforeEdit,
            "Editor content, before edit",
            editor,
        );
    }

    if (stepFunction) {
        await stepFunction(editor);
    }

    if (contentAfterEdit) {
        await compareFunction(
            getContent(el, config.options),
            contentAfterEdit,
            "Editor content, after edit",
            editor,
        );
    }
    if (contentAfter) {
        const content = editor.getContent();
        dispatchCleanForSave(editor, { root: el, preserveSelection: true });
        const innerHTML = el.innerHTML;
        await compareFunction(
            getContent(el, config.options),
            contentAfter,
            "Editor content, after clean",
            editor,
        );
        await compareFunction(
            content,
            innerHTML,
            "Value from editor.getContent()",
            editor,
        );
    }
    destroy(editorComponent);
    await willBeDestroyed;
}
/**
 * @param {Object} props
 * @returns { Promise<{el: HTMLElement, wysiwyg: Wysiwyg}> }
 */
export async function setupWysiwyg(props = {}) {
    const content = props.content;
    delete props.content;
    const wysiwyg = await mountWithCleanup(Wysiwyg, { props });
    const el = /** @type {HTMLElement} */ (
        queryOne(`${props.iframe ? ":iframe " : ""}.odoo-editor-editable`)
    );
    if (content) {
        setContent(el, content);
    }
    return { wysiwyg, el };
}

export function insertTestHtml(innerHtml) {
    const container = getFixture();
    container.classList.add("odoo-editor-editable");
    container.setAttribute("contenteditable", "true");
    container.innerHTML = innerHtml;
    return container.childNodes;
}
