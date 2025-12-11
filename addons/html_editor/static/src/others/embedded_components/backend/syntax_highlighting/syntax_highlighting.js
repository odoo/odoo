import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { Component, markup, onMounted, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import {
    getPreValue,
    highlightPre,
} from "../../core/syntax_highlighting/syntax_highlighting_utils";
import { CodeToolbar } from "./code_toolbar";

export class EmbeddedSyntaxPlainInput extends Component {
    static template = "html_editor.EmbeddedSyntaxPlainInput";
    static props = {
        onFocus: { type: Function },
        embeddedState: { type: Object },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.preRef = useRef("pre");
        onMounted(() => {
            const pre = this.preRef.el;
            pre.innerHTML = markup(this.props.embeddedState.value);
        });
    }
    onInput(ev) {
        this.props.embeddedState.value = markup(this.preRef.el.innerHTML);
    }
}

export class EmbeddedSyntaxHighlightingInput extends Component {
    static template = "html_editor.EmbeddedSyntaxHighlightingInput";
    static props = {
        value: { type: String },
        onTextareaFocus: { type: Function },
        embeddedState: { type: Object },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.preRef = useRef("pre");
        this.textareaRef = useRef("textarea");

        onWillStart(() => this.loadPrism());
        onMounted(() => {
            this.document = this.textareaRef.el.ownerDocument;
            this.highlight();
        });

        useEffect(this.highlight.bind(this), () => [
            this.props.embeddedState.value,
            this.props.embeddedState.languageId,
        ]);
    }

    /**
     * Load the Prism library. This function exists only so it can be overridden
     * in tests.
     */
    loadPrism() {
        return loadBundle(
            `html_editor.assets_prism${cookie.get("color_scheme") === "dark" ? "_dark" : ""}`,
            { targetDoc: this.props.host.ownerDocument }
        );
    }

    /**
     * Highlight the content of the pre.
     */
    highlight() {
        const pre = this.preRef.el;
        const textarea = this.textareaRef.el;
        const focus = this.document.activeElement === textarea;

        highlightPre(pre, this.props.embeddedState.value, this.props.embeddedState.languageId);

        // Ensure the values match.
        const preValue = getPreValue(pre);
        if (textarea.value !== preValue) {
            textarea.value = preValue;
        }
        if (focus) {
            textarea.focus({ preventScroll: true });
            this.props.onTextareaFocus();
        }
        this.props.embeddedState.value = textarea.value;
    }

    onInput() {
        const textarea = this.textareaRef.el;
        textarea.focus();
        this.props.onTextareaFocus();
        this.props.embeddedState.value = textarea.value;
        this.highlight();
    }

    /**
     * Handle tabulation in the textarea.
     *
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        const textarea = this.textareaRef.el;
        if (ev.key === "Tab") {
            ev.preventDefault();
            const tabSize = +getComputedStyle(textarea).tabSize || 4;
            const tab = " ".repeat(tabSize);
            const { selectionStart, selectionEnd } = textarea;
            const collapsed = selectionStart === selectionEnd;
            let start = textarea.value.slice(0, selectionStart).lastIndexOf("\n");
            start = start === -1 ? 0 : start;
            let newValue = "";
            let spacesRemovedAtStart = 0;
            if (ev.shiftKey) {
                // Remove tabs.
                let end = textarea.value.slice(selectionEnd, textarea.value.length).indexOf("\n");
                end = end === -1 ? 0 : end;
                end = selectionEnd + end;
                // From 0 to the last \n before selection start.
                newValue = textarea.value.slice(0, start);
                // From the last \n before selection start to selection end.
                const regex = new RegExp(`(\n|^)( |\u00A0){1,${tabSize}}`, "g");
                const startSlice = textarea.value.slice(start, selectionStart);
                const cleanStartSlice = startSlice.replace(regex, "$1");
                spacesRemovedAtStart = startSlice.length - cleanStartSlice.length;
                newValue += cleanStartSlice;
                newValue += textarea.value.slice(selectionStart, selectionEnd).replace(regex, "$1");
                newValue += textarea.value.slice(selectionEnd, end).replace(regex, "$1");
                // From selection end to end.
                newValue += textarea.value.slice(end, textarea.value.length);
            } else {
                // Insert tabs.
                if (collapsed && /\S/.test(textarea.value.slice(start, selectionStart))) {
                    newValue =
                        textarea.value.slice(0, selectionStart) +
                        tab +
                        textarea.value.slice(selectionStart, textarea.value.length);
                } else {
                    // From 0 to the last \n before selection start.
                    newValue = start ? textarea.value.slice(0, start) : tab;
                    // From the last \n before selection start to selection end.
                    newValue += textarea.value
                        .slice(start, selectionEnd)
                        .replaceAll("\n", `\n${tab}`);
                    // From selection end to end.
                    newValue += textarea.value.slice(selectionEnd, textarea.value.length);
                }
            }
            const insertedChars = newValue.length - textarea.value.length;
            textarea.value = newValue;
            const newStart = selectionStart + (ev.shiftKey ? -spacesRemovedAtStart : tabSize);
            const newEnd = collapsed ? newStart : selectionEnd + insertedChars;
            textarea.setSelectionRange(newStart, newEnd, textarea.selectionDirection);
            this.props.embeddedState.value = textarea.value;
        }
    }

    /**
     * Ensure the pre and textarea's scrolls match so they remain aligned.
     */
    onScroll() {
        const pre = this.preRef.el;
        const textarea = this.textareaRef.el;
        pre.scrollTop = textarea.scrollTop;
        pre.scrollLeft = textarea.scrollLeft;
    }
}

export class EmbeddedSyntaxHighlightingComponent extends Component {
    static template = "html_editor.EmbeddedSyntaxHighlighting";
    static components = { CodeToolbar, EmbeddedSyntaxPlainInput, EmbeddedSyntaxHighlightingInput };
    static props = {
        value: { type: String },
        languageId: { type: String },
        onTextareaFocus: { type: Function },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.state = useState({
            host: this.props.host,
        });
        this.embeddedState = useEmbeddedState(this.props.host);
    }

    /**
     * Change the language when selecting a new one via the code toolbar.
     *
     * @param {string} languageId
     */
    onLanguageChange(languageId) {
        if (languageId && this.embeddedState.languageId !== languageId) {
            this.adaptValue(
                languageId === "plaintext",
                this.embeddedState.languageId === "plaintext"
            );
            this.embeddedState.languageId = languageId;
        }
    }

    adaptValue(toMarkup, fromMarkup) {
        if (toMarkup === fromMarkup) {
            return;
        }
        const el = document.createElement("pre");
        if (toMarkup) {
            el.innerText = this.embeddedState.value;
            this.embeddedState.value = markup(el.innerHTML);
        } else {
            el.innerHTML = markup(this.embeddedState.value);
            for (const br of el.querySelectorAll("br")) {
                br.replaceWith(document.createTextNode("\n"));
            }
            this.embeddedState.value = getPreValue(el);
        }
    }

    getContent() {
        if (this.embeddedState.languageId === "plaintext") {
            const el = document.createElement("pre");
            el.innerHTML = this.embeddedState.value;
            for (const br of el.querySelectorAll("br")) {
                br.replaceWith(document.createTextNode("\n"));
            }
            return el.textContent;
        }
        return this.embeddedState.value;
    }
}

export const syntaxHighlightingEmbedding = {
    name: "syntaxHighlighting",
    Component: EmbeddedSyntaxHighlightingComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) => new StateChangeManager(config),
};
