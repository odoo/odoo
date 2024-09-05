import { Wysiwyg } from "@html_editor/wysiwyg";
import { expect, getFixture } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { getContent, getSelection, setContent } from "./selection";
import { animationFrame } from "@odoo/hoot-mock";

export const Direction = {
    BACKWARD: "BACKWARD",
    FORWARD: "FORWARD",
};

class TestEditor extends Component {
    static template = xml`
        <t t-if="props.styleContent">
            <style t-esc="props.styleContent"></style>
        </t>
        <Wysiwyg t-props="wysiwygProps" />`;
    static components = { Wysiwyg };
    static props = ["wysiwygProps", "content", "styleContent?", "onMounted?"];

    setup() {
        const props = this.props;
        const content = props.content;
        this.wysiwygProps = Object.assign({}, this.props.wysiwygProps);
        const iframe = this.props.wysiwygProps.iframe;
        const oldOnLoad = this.wysiwygProps.onLoad;
        this.wysiwygProps.onLoad = function (editor) {
            const oldAttach = editor.attachTo;
            editor.attachTo = function (el) {
                // @todo @phoenix move it to setupMultiEditor
                if (iframe) {
                    // el is here the body
                    const content = props.content || "";
                    var html = `<div>${content}</div><style>${props.styleContent}</style>`;
                    el.innerHTML = html;
                    el = el.firstChild;
                }
                if (props.content) {
                    el.setAttribute("contenteditable", true); // so we can focus it if needed
                    const configSelection = getSelection(el, props.content);
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
 * @param { string } content
 * @param {TestConfig} [options]
 * @returns { Promise<{el: HTMLElement; editor: Editor; }> }
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
    await mountWithCleanup(TestEditor, {
        props: {
            content,
            wysiwygProps,
            styleContent,
            onMounted: options.onMounted,
        },
        env: options.env,
    });

    // awaiting for mountWithCleanup is not enough when mounted in an iframe,
    // @see Wysiwyg.onMounted
    const editor = await attachedEditor;
    const plugins = new Map(
        editor.plugins.map((plugin) => {
            return [plugin.constructor.name, plugin];
        })
    );
    if (plugins.get("embedded_components")) {
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
    };
}

/**
 * @typedef { Object } TestEditorConfig
 * @property { string } contentBefore
 * @property { string } [contentBeforeEdit]
 * @property { (editor: Editor) => any } [stepFunction]
 * @property { string } [contentAfter]
 * @property { string } [contentAfterEdit]
 * @property { (content: string, expected: string, phase: string) => void } [compareFunction]
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
                message: `(testEditor) ${phase} is strictly equal to %actual%"`,
            });
        };
    }
    const { el, editor } = await setupEditor(contentBefore, config);
    // The HISTORY_STAGE_SELECTION should have been triggered by the click on
    // the editable. As we set the selection programmatically, we dispatch the
    // selection here for the commands that relies on it.
    // If the selection of the editor would be programatically set upon start
    // (like an autofocus feature), it would be the role of the autofocus
    // feature to trigger the HISTORY_STAGE_SELECTION.
    editor.dispatch("HISTORY_STAGE_SELECTION");
    if (config.props?.iframe) {
        expect("iframe").toHaveCount(1);
    }

    if (contentBeforeEdit) {
        // we should do something before (sanitize)
        compareFunction(getContent(el), contentBeforeEdit, "Editor content, before edit");
    }

    if (stepFunction) {
        await stepFunction(editor);
    }

    if (contentAfterEdit) {
        compareFunction(getContent(el), contentAfterEdit, "Editor content, after edit");
    }
    if (contentAfter) {
        const content = editor.getContent();
        editor.dispatch("CLEAN_FOR_SAVE", { root: el, preserveSelection: true });
        compareFunction(getContent(el), contentAfter, "Editor content, after clean");
        compareFunction(content, el.innerHTML, "Value from editor.getContent()");
    }
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
