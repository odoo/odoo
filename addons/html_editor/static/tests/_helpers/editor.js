import { Wysiwyg } from "@html_editor/wysiwyg";
import { destroy, expect, getFixture } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { Component, markup, onWillDestroy, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { getContent, getSelection, setContent } from "./selection";
import { Deferred, animationFrame, tick } from "@odoo/hoot-mock";
import { dispatchCleanForSave } from "./dispatch";
import { fixInvalidHTML } from "@html_editor/utils/sanitize";
import { toExplicitString } from "@web/../lib/hoot/hoot_utils";

export const Direction = {
    BACKWARD: "BACKWARD",
    FORWARD: "FORWARD",
};

// A generic base64 image for testing
export const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

class TestEditor extends Component {
    static template = xml`
        <t t-if="props.styleContent">
            <style t-esc="props.styleContent"></style>
        </t>
        <Wysiwyg t-props="wysiwygProps" />`;
    static components = { Wysiwyg };
    static props = ["wysiwygProps", "content", "styleContent?", "onMounted?", "onWillDestroy?"];

    setup() {
        const props = this.props;
        const content = fixInvalidHTML(props.content);
        this.wysiwygProps = Object.assign({}, this.props.wysiwygProps);
        const iframe = this.props.wysiwygProps.iframe;
        const oldOnLoad = this.wysiwygProps.onLoad;
        this.wysiwygProps.onLoad = function (editor) {
            const oldAttach = editor.attachTo;
            editor.attachTo = function (el) {
                // @todo @phoenix move it to setupMultiEditor
                if (iframe) {
                    // el is here the body
                    var html = `<div>${content || ""}</div><style>${props.styleContent}</style>`;
                    el.innerHTML = html;
                    el = el.firstChild;
                }
                if (content) {
                    el.setAttribute("contenteditable", true); // so we can focus it if needed
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
        if (this.wysiwygProps.config.resources?.embedded_components) {
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
 * @typedef { import("@html_editor/plugin").Editor } Editor
 */

/**
 * @param { string } content
 * @param {TestConfig} [options]
 * @returns { Promise<{el: HTMLElement; editor: Editor; plugins: Map<string,Plugin>}> }
 */
export async function setupEditor(content, options = {}) {
    const wysiwygProps = Object.assign({}, options.props);
    wysiwygProps.config = options.config || {};
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
            // TODO: Move the markup call up the chain and call markup at source.
            // markup: Not the correct place to call markup as content can be anything but would be okay for the tests.
            content: markup(content),
            wysiwygProps,
            styleContent,
            onMounted: options.onMounted,
            onWillDestroy: options.onWillDestroy,
        },
        env: options.env,
    });

    // awaiting for mountWithCleanup is not enough when mounted in an iframe,
    // @see Wysiwyg.onMounted
    const editor = await attachedEditor;
    const plugins = new Map(editor.plugins.map((plugin) => [plugin.constructor.id, plugin]));
    if (plugins.get("embeddedComponents")) {
        // await an extra animation frame for embedded components mounting
        // TODO @phoenix: would be more accurate to register mounting
        // promises in embedded_component_plugin and await them, change this
        // if there is an issue.
        await animationFrame();
    }

    // @todo: return editor, tests can destructure const { editable } = ... if they want
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
 * TODO maybe we should add "styleContent" or use setupEditor directly
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
                    expected
                )}`,
            });
        };
    }
    delete config.props?.mobile;
    const willBeDestroyed = new Deferred();
    config.onWillDestroy = () => willBeDestroyed.resolve();
    const { el, editor, editorComponent } = await setupEditor(contentBefore, config);
    // The stageSelection should have been triggered by the click on
    // the editable. As we set the selection programmatically, we dispatch the
    // selection here for the commands that relies on it.
    // If the selection of the editor would be programatically set upon start
    // (like an autofocus feature), it would be the role of the autofocus
    // feature to trigger the stageSelection.
    editor.shared.history.stageSelection();

    if (config.props?.iframe) {
        expect(".o-wysiwyg iframe").toHaveCount(1);
    }

    // Wait for selectionchange handlers to react before any actual testing.
    await tick();

    if (contentBeforeEdit) {
        // we should do something before (sanitize)
        await compareFunction(
            getContent(el, config.options),
            contentBeforeEdit,
            "Editor content, before edit",
            editor
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
            editor
        );
    }
    if (contentAfter) {
        // Test the saved value, with added cursor markers for convenience of testing.
        const content = editor.getContent(); // Saved value.
        dispatchCleanForSave(editor, { root: el, preserveSelection: true });
        const innerHTML = el.innerHTML; // Cleaned value without cursors.
        await compareFunction(
            getContent(el, config.options),
            contentAfter,
            "Editor content, after clean",
            editor
        );
        // Test that the saved value matches the cleaned value tested above.
        await compareFunction(content, innerHTML, "Value from editor.getContent()", editor);
    }
    destroy(editorComponent);
    await willBeDestroyed;
}
/**
 * @todo: remove this?
 *
 * @param {Object} props
 * @returns { Promise<{el: HTMLElement, wysiwyg: Wysiwyg}> } result
 */
export async function setupWysiwyg(props = {}) {
    const content = props.content;
    delete props.content;
    const wysiwyg = await mountWithCleanup(Wysiwyg, { props });
    const el = /** @type {HTMLElement} **/ (
        queryOne(`${props.iframe ? ":iframe " : ""}.odoo-editor-editable`)
    );
    if (content) {
        // force selection to be put properly
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
