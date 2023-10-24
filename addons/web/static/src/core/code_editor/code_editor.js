/** @odoo-module */
import { Component, onWillDestroy, onWillStart, useEffect, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { useDebounced } from "@web/core/utils/timing";

function onResized(ref, callback) {
    const _ref = typeof ref === "string" ? useRef(ref) : ref;
    const resizeObserver = new ResizeObserver(callback);

    useEffect(
        (el) => {
            if (el) {
                resizeObserver.observe(el);
                return () => resizeObserver.unobserve(el);
            }
        },
        () => [_ref.el]
    );

    onWillDestroy(() => {
        resizeObserver.disconnect();
    });
}

export class CodeEditor extends Component {
    static template = "web.CodeEditor";
    static components = {};
    static props = {
        mode: {
            type: String,
            optional: true,
            validate: (mode) => CodeEditor.MODES.includes(mode),
        },
        value: { validate: (v) => typeof v === "string", optional: true },
        readonly: { type: Boolean, optional: true },
        onChange: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
        class: { type: String, optional: true },
        theme: {
            type: String,
            optional: true,
            validate: (theme) => CodeEditor.THEMES.includes(theme),
        },
        maxLines: { type: Number, optional: true },
        sessionId: { type: [Number, String], optional: true },
    };
    static defaultProps = {
        readonly: false,
        value: "",
        onChange: () => {},
        class: "",
        theme: "",
        sessionId: 1,
    };

    static MODES = ["js", "xml", "qweb", "scss", "python"];
    static THEMES = ["", "monokai"];

    setup() {
        this.editorRef = useRef("editorRef");

        onWillStart(async () => await loadBundle("web.ace_lib"));

        const sessions = {};
        // The ace library triggers the "change" event even if the change is
        // programmatic. Even worse, it triggers 2 "change" events in that case,
        // one with the empty string, and one with the new value. We only want
        // to notify the parent of changes done by the user, in the UI, so we
        // use this flag to filter out noisy "change" events.
        let ignoredAceChange = false;
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }

                // keep in closure
                const aceEditor = window.ace.edit(el);
                this.aceEditor = aceEditor;

                this.aceEditor.setOptions({
                    maxLines: this.props.maxLines,
                    showPrintMargin: false,
                    useWorker: false,
                });
                this.aceEditor.$blockScrolling = true;

                const session = aceEditor.getSession();
                if (!sessions[this.props.sessionId]) {
                    sessions[this.props.sessionId] = session;
                }
                aceEditor.setValue(this.props.value);
                session.on("change", () => {
                    if (this.props.onChange && !ignoredAceChange) {
                        this.props.onChange(this.aceEditor.getValue());
                    }
                });
                this.aceEditor.on("blur", () => {
                    if (this.props.onBlur) {
                        this.props.onBlur();
                    }
                });

                return () => {
                    aceEditor.destroy();
                };
            },
            () => [this.editorRef.el]
        );

        useEffect(
            (theme) => this.aceEditor.setTheme(theme ? `ace/theme/${theme}` : ""),
            () => [this.props.theme]
        );

        useEffect(
            (readonly) => {
                this.aceEditor.setOptions({
                    readOnly: readonly,
                    highlightActiveLine: !readonly,
                    highlightGutterLine: !readonly,
                });

                this.aceEditor.renderer.setOptions({
                    displayIndentGuides: !readonly,
                    showGutter: !readonly,
                });

                this.aceEditor.renderer.$cursorLayer.element.style.display = readonly
                    ? "none"
                    : "block";
            },
            () => [this.props.readonly]
        );

        useEffect(
            (sessionId, mode, value) => {
                let session = sessions[sessionId];
                if (session) {
                    if (session.getValue() !== value) {
                        ignoredAceChange = true;
                        session.setValue(value);
                        ignoredAceChange = false;
                    }
                } else {
                    session = new window.ace.EditSession(value);
                    session.setUndoManager(new window.ace.UndoManager());
                    session.setOptions({
                        useWorker: false,
                        tabSize: 2,
                        useSoftTabs: true,
                    });
                    session.on("change", () => {
                        if (this.props.onChange && !ignoredAceChange) {
                            this.props.onChange(this.aceEditor.getValue());
                        }
                    });
                    sessions[sessionId] = session;
                }
                session.setMode(mode ? `ace/mode/${mode}` : "");
                this.aceEditor.setSession(session);
            },
            () => [this.props.sessionId, this.props.mode, this.props.value]
        );

        const debouncedResize = useDebounced(() => {
            if (this.aceEditor) {
                this.aceEditor.resize();
            }
        }, 250);

        onResized(this.editorRef, debouncedResize);
    }
}
