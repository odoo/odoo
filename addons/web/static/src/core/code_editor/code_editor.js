import { useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { Component, onWillStart, markRaw, props, status, types as t } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { useDebounced } from "../utils/timing";
import { Reactive } from "../utils/reactive";

class CodeEditorState extends Reactive {
    /**@protected*/
    _session = null;
    /**@protected*/
    _canUndo = false;
    /**@protected*/
    _canRedo = false;

    get canUndo() {
        return this._session && this._canUndo;
    }

    get canRedo() {
        return this._session && this._canRedo;
    }

    undo() {
        this._session?.getUndoManager().undo();
        this._update();
    }

    redo() {
        this._session?.getUndoManager().redo();
        this._update();
    }

    /** @protected */
    _setSession(session) {
        this._session = session ? markRaw(session) : null;
        this._update();
    }

    /**@protected */
    _update() {
        if (this._session) {
            const undoManager = this._session.getUndoManager();
            this._canUndo = undoManager.canUndo();
            this._canRedo = undoManager.canRedo();
        }
    }
}

/**
 * Hook used to interact with the CodeEditor undo state and to subscribe to changes.
 * @returns {CodeEditorState}
 */
export function useCodeEditorState() {
    return useState(new CodeEditorState());
}

export class CodeEditor extends Component {
    static template = "web.CodeEditor";
    static components = {};
    static MODES = ["javascript", "xml", "qweb", "scss", "python", "json", "bash"];
    static THEMES = ["", "monokai"];

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
            "cursorPosition?": t.object({
                "column?": t.number(),
                "row?": t.number(),
            }),
            "onCursorPositionChange?": t.function(),
            "showLineNumbers?": t.boolean(),
            "lineWrapping?": t.boolean(),
            "editorState?": t.instanceOf(CodeEditorState),
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

    setup() {
        this.editorRef = useRef("editorRef");
        this.state = useState({
            activeMode: undefined,
        });

        onWillStart(async () => await loadBundle("web.ace_lib"));

        const sessions = {};

        const onCursorChange = useDebounced(() => {
            this.props.onCursorPositionChange?.(this.aceEditor.getCursorPosition());
        }, "animationFrame");

        // The ace library triggers the "change" event even if the change is
        // programmatic. Even worse, it triggers 2 "change" events in that case,
        // one with the empty string, and one with the new value. We only want
        // to notify the parent of changes done by the user, in the UI, so we
        // use this flag to filter out noisy "change" events.
        let ignoredAceChange = false;
        const onChange = () => {
            if (this.props.editorState) {
                const session = this.aceEditor.getSession();
                this.props.editorState._canUndo = session.getUndoManager().canUndo();
                this.props.editorState._canRedo = session.getUndoManager().canRedo();
            }

            if (this.props.onChange && !ignoredAceChange) {
                this.props.onChange(this.aceEditor.getValue());
            }

            onCursorChange();
        };

        useLayoutEffect(
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
                    wrap: this.props.lineWrapping,
                });
                this.aceEditor.$blockScrolling = true;

                this.aceEditor.on("changeMode", () => {
                    this.state.activeMode = this.aceEditor.getSession().$modeId.split("/").at(-1);
                });

                const session = aceEditor.getSession();
                if (!sessions[this.props.sessionId]) {
                    sessions[this.props.sessionId] = session;
                }
                session.setValue(this.props.value);
                session.on("change", onChange);

                this.aceEditor.on("blur", () => {
                    if (this.props.onBlur) {
                        this.props.onBlur();
                    }
                });

                // Wait for ace to be fully operational
                window.requestAnimationFrame(() => {
                    if (status(this) != "destroyed") {
                        this.setCursorPosition(this.props.cursorPosition);
                    }
                });

                if (this.props.editorState) {
                    this.props.editorState._setSession(session);
                }

                return () => {
                    if (this.props.editorState) {
                        this.props.editorState._setSession(null);
                        this.props.editorState._canUndo = false;
                        this.props.editorState._canRedo = false;
                    }
                    aceEditor.destroy();
                };
            },
            () => [this.editorRef.el]
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
                    session.on("change", onChange);
                    sessions[sessionId] = session;
                }

                session.setMode(this.aceMode);
                this.aceEditor.setSession(session);
            },
            () => [this.props.sessionId, this.props.mode, this.props.value]
        );

        useLayoutEffect(
            (cursorPosition) => {
                this.setCursorPosition(cursorPosition);
            },
            () => [this.props.cursorPosition]
        );
    }

    get aceMode() {
        const mode = this.props.mode;
        if (mode) {
            return {
                path: `ace/mode/${mode}`,
                ...(this.props.modeOptions || {}),
            };
        }
        return "";
    }

    setCursorPosition(cursorPosition) {
        if (cursorPosition && this.aceEditor) {
            const pos = {
                row: cursorPosition.row || 0,
                column: cursorPosition.column || 0,
            };

            this.aceEditor.focus();
            this.aceEditor.selection.moveToPosition(pos);
            this.aceEditor.renderer.scrollCursorIntoView(pos, 0.5);
        }
    }
}
