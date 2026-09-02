import { Component, onMounted, onWillDestroy, signal, useEffect, useProps, t } from "@odoo/owl";
import { cookie } from "@web/core/browser/cookie";

export class IframeInput extends Component {
    static template = "html_editor.IframeInput";
    static props = {
        // data / value
        value: { type: [String, Number] },
        inputAttrs: { type: Object, optional: true },

        // styling
        iframeClass: { type: String, optional: true },
        inputStyle: { type: String, optional: true },

        // events (handlers)
        onBlur: { type: Function, optional: true },
        onChange: { type: Function, optional: true },
        onClick: { type: Function, optional: true },
        onFocus: { type: Function, optional: true },
        onInput: { type: Function, optional: true },
        onKeydown: { type: Function, optional: true },
    };

    // Refs (DOM access): the iframe is bound with `t-ref`, while the input,
    // created programmatically inside the iframe, is set imperatively.
    iframeRef = useProps.static(
        "iframeRef",
        t.signal(t.ref()).optional(() => signal.ref())
    );
    inputRef = useProps.static("inputRef", t.signal(t.ref()).optional());

    setup() {
        onMounted(() => {
            this.iframeEl = this.iframeRef();

            this.initInput = () => {
                const iframeDoc = this.iframeEl.contentWindow.document;

                // Skip if already initialized or body is missing.
                if (this.input?.closest("body") === iframeDoc.body || !iframeDoc.body) {
                    return;
                }

                const isDarkMode = cookie.get("color_scheme") === "dark";
                const styleEl = iframeDoc.createElement("style");
                styleEl.textContent = `
                    /* Hides the number input's spin buttons (chrome, edge, safari) */
                    input::-webkit-outer-spin-button,
                    input::-webkit-inner-spin-button {
                        -webkit-appearance: none;
                        margin: 0;
                    }
                    /* Hides the number input's spin buttons (firefox) */
                    input[type="number"] {
                        -moz-appearance: textfield;
                    }
                    body {
                        padding: 0;
                        margin: 0;
                    }
                    input {
                        width: 100%;
                        height: 100%;
                        outline: none;
                        text-align: center;
                        border: none;
                        background-color: ${isDarkMode ? "#25262b" : "#FFF"};
                        color: ${isDarkMode ? "#FFF" : "#000"};
                        ${this.props.inputStyle || ""}
                    }
                `;
                iframeDoc.head.appendChild(styleEl);

                this.input = iframeDoc.createElement("input");
                this.input.autocomplete = "off";
                for (const [key, val] of Object.entries(this.props.inputAttrs || {})) {
                    this.input.setAttribute(key, val);
                }
                this.input.value = this.props.value;

                iframeDoc.body.appendChild(this.input);
                this._bindInputEvents();
                this.inputRef?.set(this.input);
            };

            if (this.iframeEl.contentDocument.readyState === "complete") {
                this.initInput();
            }
            // If iframe is moved around in DOM, it restarts from scratch and needs to be repopulated.
            this.iframeEl.addEventListener("load", this.initInput);
        });

        onWillDestroy(() => {
            this.iframeEl?.removeEventListener("load", this.initInput);
            if (this.input && this._handlers) {
                for (const [event, handler] of Object.entries(this._handlers)) {
                    this.input.removeEventListener(event, handler);
                }
            }
            this.input = null;
        });

        useEffect(() => {
            void this.props.value; // subscribe to value prop changes
            if (this.input) {
                // Update value whenever it changes.
                this.input.value = this.props.value;
            }
        });
    }

    _bindInputEvents() {
        const handlers = {
            blur: this.props.onBlur,
            change: this.props.onChange,
            click: this.props.onClick,
            focus: this.props.onFocus,
            input: this.props.onInput,
            keydown: this.props.onKeydown,
        };
        this._handlers = {};
        for (const [event, handler] of Object.entries(handlers)) {
            if (!handler) {
                continue;
            }
            this._handlers[event] = handler;
            this.input.addEventListener(event, handler);
        }
    }
}
