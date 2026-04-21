import {
    Component,
    onMounted,
    onWillDestroy,
    onWillStart,
    props,
    signal,
    types as t,
} from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { useLayoutEffect } from "@web/owl2/utils";

export class CodeEditor extends Component {
    static template = "web.CodeEditor";

    /** @type {AceAjax.Editor | null} */
    aceEditor = null;

    activeMode = signal(null, t.or([t.string(), t.literal(null)]));
    editorRef = signal(null, t.ref(HTMLDivElement));
    props = props(
        {
            "mode?": t.selection(CodeEditor.MODES),
            "modeOptions?": t.object(),
            "value?": t.string(),
            "readonly?": t.boolean(),
            "onChange?": t.function(),
            "onBlur?": t.function(),
            "class?": t.string(),
            "theme?": t.selection(CodeEditor.THEMES),
            "maxLines?": t.number(),
            "sessionId?": t.or([t.number(), t.string()]),
            "initialCursorPosition?": t.object({
                "column?": t.number(),
                "row?": t.number(),
            }),
            "showLineNumbers?": t.boolean(),
            "lineWrapping?": t.boolean(),
        },
        {
            readonly: false,
            value: "",
            onChange: () => {},
            class: "",
            theme: "",
            sessionId: 1,
            showLineNumbers: true,
        }
    );
    sessions = {};

    static MODES = ["javascript", "xml", "qweb", "scss", "python", "json", "bash"];
    static THEMES = ["", "monokai"];

    setup() {
        onWillStart(() => loadBundle("web.ace_lib"));

        // The ace library triggers the "change" event even if the change is
        // programmatic. Even worse, it triggers 2 "change" events in that case,
        // one with the empty string, and one with the new value. We only want
        // to notify the parent of changes done by the user, in the UI, so we
        // use this flag to filter out noisy "change" events.
        let ignoredAceChange = false;
        useLayoutEffect(
            (el) => {
                if (!el) {
                    return;
                }

                this.aceEditor = window.ace.edit(el, {
                    maxLines: this.props.maxLines,
                    showPrintMargin: false,
                    useWorker: false,
                    wrap: this.props.lineWrapping,
                });
                this.aceEditor.on("changeMode", () => {
                    this.activeMode.set(
                        this.aceEditor.getSession().$modeId.split("/").at(-1) ?? null
                    );
                });
                this.aceEditor.on("blur", () => {
                    if (this.props.onBlur) {
                        this.props.onBlur();
                    }
                });

                const session = this.aceEditor.getSession();
                session.setValue(this.props.value);
                session.on("change", () => {
                    if (this.props.onChange && !ignoredAceChange) {
                        this.props.onChange(
                            this.aceEditor.getValue(),
                            this.aceEditor.getCursorPosition()
                        );
                    }
                });

                this.sessions[this.props.sessionId] ||= session;

                return this.aceEditor.destroy.bind(this.aceEditor);
            },
            () => [this.editorRef()]
        );

        useLayoutEffect(
            (theme) => this.aceEditor.setTheme(theme ? `ace/theme/${theme}` : ""),
            () => [this.props.theme]
        );

        useLayoutEffect(
            (readonly, showLineNumbers) => {
                this.aceEditor.setOptions({
                    readOnly: readonly,
                    highlightActiveLine: !readonly,
                    highlightGutterLine: !readonly,
                });

                this.aceEditor.renderer.setOptions({
                    displayIndentGuides: !readonly,
                    showGutter: !readonly && showLineNumbers,
                });

                this.aceEditor.renderer.$cursorLayer.element.style.display = readonly
                    ? "none"
                    : "block";
            },
            () => [this.props.readonly, this.props.showLineNumbers]
        );

        useLayoutEffect(
            (sessionId, mode, modeOptions, value) => {
                let session = this.sessions[sessionId];
                if (session) {
                    if (session.getValue() !== value) {
                        ignoredAceChange = true;
                        session.setValue(value);
                        ignoredAceChange = false;
                    }
                } else {
                    session = window.ace.createEditSession(value);
                    session.setOptions({
                        useWorker: false,
                        tabSize: 2,
                        useSoftTabs: true,
                    });
                    session.on("change", () => {
                        if (this.props.onChange && !ignoredAceChange) {
                            this.props.onChange(
                                this.aceEditor.getValue(),
                                this.aceEditor.getCursorPosition()
                            );
                        }
                    });
                    this.sessions[sessionId] = session;
                }
                session.setMode(mode ? { path: `ace/mode/${mode}`, ...modeOptions } : "");
                this.aceEditor.setSession(session);
            },
            () => [this.props.sessionId, this.props.mode, this.props.modeOptions, this.props.value]
        );

        const initialCursorPosition = this.props.initialCursorPosition;
        if (initialCursorPosition) {
            onMounted(() => {
                // Wait for ace to be fully operational
                requestAnimationFrame(() => {
                    if (!this.aceEditor) {
                        return;
                    }
                    this.aceEditor.focus();
                    const { row, column } = initialCursorPosition;
                    const pos = {
                        row: row || 0,
                        column: column || 0,
                    };
                    this.aceEditor.selection.moveToPosition(pos);
                    this.aceEditor.renderer.scrollCursorIntoView(pos, 0.5);
                });
            });
        }

        onWillDestroy(() => {
            this.sessions = {};
            this.aceEditor?.destroy();
            this.aceEditor = null;
        });
    }
}
