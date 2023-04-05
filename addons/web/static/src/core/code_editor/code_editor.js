/** @odoo-module */
import { Component, onWillDestroy, onWillStart, useEffect, useRef } from "@odoo/owl";
import { getBundle, loadBundle } from "@web/core/assets";
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
        value: { type: String, optional: true },
        onChange: { type: Function, optional: true },
        class: { type: String, optional: true },
        theme: {
            type: String,
            optional: true,
            validate: (theme) => CodeEditor.THEMES.includes(theme),
        },
    };
    static defaultProps = {
        value: "",
        onChange: () => {},
        class: "",
        theme: "",
    };

    static MODES = ["js", "xml", "qweb", "scss", "python"];
    static THEMES = ["", "monokai"];

    setup() {
        this.editorRef = useRef("editorRef");

        onWillStart(async () => loadBundle(await getBundle("web.ace_lib")));

        useEffect(
            (el) => {
                if (!el) {
                    return;
                }

                // keep in closure
                const aceEditor = window.ace.edit(el);
                this.aceEditor = aceEditor;
                this.aceEditor.session.setUseWorker(false);
                this.aceEditor.setValue(this.props.value);

                this.aceEditor.session.on("change", () => {
                    if (this.props.onChange) {
                        this.props.onChange(this.aceEditor.getValue());
                    }
                });

                return () => {
                    aceEditor.destroy();
                };
            },
            () => [this.editorRef.el]
        );

        useEffect(
            (value) => {
                if (value !== this.aceEditor.getValue()) {
                    this.aceEditor.setValue(value);
                }
            },
            () => [this.props.value]
        );

        useEffect(
            (mode) => this.aceEditor.session.setMode(mode ? `ace/mode/${mode}` : ""),
            () => [this.props.mode]
        );

        useEffect(
            (theme) => this.aceEditor.setTheme(theme ? `ace/theme/${theme}` : "textmate"),
            () => [this.props.theme]
        );

        this.debouncedResize = useDebounced(() => {
            if (this.aceEditor) {
                this.aceEditor.resize();
            }
        }, 250);

        onResized(this.editorRef, () => this.debouncedResize());
    }
}
