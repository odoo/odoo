import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import {
    getPreValue,
    highlightPre,
} from "../../core/syntax_highlighting/syntax_highlighting_utils";

const LANGUAGES = {
    plaintext: "Plain Text",
    markdown: "Markdown",
    javascript: "Javascript",
    typescript: "Typescript",
    jsdoc: "JSDoc",
    java: "Java",
    python: "Python",
    html: "HTML",
    xml: "XML",
    svg: "SVG",
    json: "JSON",
    css: "CSS",
    sass: "SASS",
    scss: "SCSS",
    sql: "SQL",
    diff: "Diff",
};

export class EmbeddedSyntaxHighlightingComponent extends Component {
    static template = "html_editor.EmbeddedSyntaxHighlighting";

    static props = {
        value: { type: String },
        languageId: { type: String },
        autofocus: { type: Boolean },
        codeToolbar: { type: Object },
        onTextareaFocus: { type: Function },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.loadPrism(); // Start loading early.
        this.state = useState({
            isActive: false,
            host: this.props.host,
            highlightedValue: "",
        });
        this.embeddedState = useEmbeddedState(this.props.host);
        this.preRef = useRef("pre");
        this.textareaRef = useRef("textarea");

        onMounted(() => {
            this.pre = this.preRef.el;
            this.textarea = this.textareaRef.el;
            this.document = this.textarea.ownerDocument;

            // Load the CSS.
            const theme = cookie.get("color_scheme") === "dark" ? "okaida" : "default";
            const prismStyleLink = document.createElement("link");
            prismStyleLink.rel = "stylesheet";
            prismStyleLink.href = `/web/static/lib/prismjs/themes/${theme}.css`;
            this.document.head.append(prismStyleLink);

            // Activate and focus the textarea if required.
            if (this.props.autofocus) {
                this.state.isActive = true;
                if (this.textarea !== this.document.activeElement) {
                    this.textarea.focus();
                    this.props.onTextareaFocus();
                }
            }
            this.loadPrism().then(this.highlight.bind(this));
        });

        // Activate/deactivate the code toolbar.
        useEffect(
            () => {
                this.props.codeToolbar.close();
                if (this.state.isActive) {
                    this.openCodeToolbar();
                }
            },
            () => [this.state.isActive]
        );

        useEffect(this.highlight.bind(this), () => [
            this.embeddedState.value,
            this.embeddedState.languageId,
        ]);
    }

    /**
     * Load the Prism library. This function exists only so it can be overridden
     * in tests.
     */
    loadPrism() {
        return loadBundle("html_editor.assets_prism");
    }

    /**
     * Highlight the content of the pre.
     */
    highlight() {
        const focus = this.document.activeElement === this.textarea;

        highlightPre(this.pre, this.embeddedState.value, this.embeddedState.languageId);

        // Ensure the values match.
        const preValue = getPreValue(this.pre);
        if (this.textarea.value !== preValue) {
            this.textarea.value = preValue;
        }
        if (focus) {
            this.textarea.focus({ preventScroll: true });
            this.props.onTextareaFocus();
        }
        this.embeddedState.value = this.textarea.value;
    }

    openCodeToolbar() {
        this.props.codeToolbar.open({
            target: this.state.host,
            props: {
                target: this.state.host,
                prismSource: this.textarea,
                languages: LANGUAGES,
                onLanguageChange: this.onLanguageChange.bind(this),
            },
        });
    }

    onInput() {
        this.textarea.focus();
        this.props.onTextareaFocus();
        this.embeddedState.value = this.textarea.value;
    }

    /**
     * Handle tabulation in the textarea.
     *
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (ev.key === "Tab") {
            ev.preventDefault();
            const tabSize = +getComputedStyle(this.textarea).tabSize || 4;
            const tab = " ".repeat(tabSize);
            const { selectionStart, selectionEnd } = this.textarea;
            const collapsed = selectionStart === selectionEnd;
            let start = this.textarea.value.slice(0, selectionStart).lastIndexOf("\n");
            start = start === -1 ? 0 : start;
            let newValue = "";
            let spacesRemovedAtStart = 0;
            if (ev.shiftKey) {
                // Remove tabs.
                let end = this.textarea.value
                    .slice(selectionEnd, this.textarea.value.length)
                    .indexOf("\n");
                end = end === -1 ? 0 : end;
                end = selectionEnd + end;
                // From 0 to the last \n before selection start.
                newValue = this.textarea.value.slice(0, start);
                // From the last \n before selection start to selection end.
                const regex = new RegExp(`(\n|^)( |\u00A0){1,${tabSize}}`, "g");
                const startSlice = this.textarea.value.slice(start, selectionStart);
                const cleanStartSlice = startSlice.replace(regex, "$1");
                spacesRemovedAtStart = startSlice.length - cleanStartSlice.length;
                newValue += cleanStartSlice;
                newValue += this.textarea.value
                    .slice(selectionStart, selectionEnd)
                    .replace(regex, "$1");
                newValue += this.textarea.value.slice(selectionEnd, end).replace(regex, "$1");
                // From selection end to end.
                newValue += this.textarea.value.slice(end, this.textarea.value.length);
            } else {
                // Insert tabs.
                if (collapsed && /\S/.test(this.textarea.value.slice(start, selectionStart))) {
                    newValue =
                        this.textarea.value.slice(0, selectionStart) +
                        tab +
                        this.textarea.value.slice(selectionStart, this.textarea.value.length);
                } else {
                    // From 0 to the last \n before selection start.
                    newValue = start ? this.textarea.value.slice(0, start) : tab;
                    // From the last \n before selection start to selection end.
                    newValue += this.textarea.value
                        .slice(start, selectionEnd)
                        .replaceAll("\n", `\n${tab}`);
                    // From selection end to end.
                    newValue += this.textarea.value.slice(selectionEnd, this.textarea.value.length);
                }
            }
            const insertedChars = newValue.length - this.textarea.value.length;
            this.textarea.value = newValue;
            const newStart = selectionStart + (ev.shiftKey ? -spacesRemovedAtStart : tabSize);
            const newEnd = collapsed ? newStart : selectionEnd + insertedChars;
            this.textarea.setSelectionRange(newStart, newEnd, this.textarea.selectionDirection);
            this.embeddedState.value = this.textarea.value;
        }
    }

    /**
     * Ensure the pre and textarea's scrolls match so they remain aligned.
     */
    onScroll() {
        this.pre.scrollTop = this.textarea.scrollTop;
        this.pre.scrollLeft = this.textarea.scrollLeft;
    }

    onHover() {
        const isLanguageSelectorOpen = !!this.document.querySelector(
            ".dropdown-menu.o_language_selector"
        );
        if (!isLanguageSelectorOpen) {
            this.state.isActive = true;
        }
    }

    onLeave(ev) {
        const isLanguageSelectorOpen = !!this.document.querySelector(
            ".dropdown-menu.o_language_selector"
        );
        if (!isLanguageSelectorOpen && !ev.relatedTarget?.closest?.(".o_code_toolbar")) {
            this.state.isActive = false;
        }
    }

    /**
     * Change the language when selecting a new one via the code toolbar.
     *
     * @param {string} languageId
     */
    onLanguageChange(languageId) {
        if (languageId && this.embeddedState.languageId !== languageId) {
            this.props.codeToolbar.close();
            this.textarea.focus();
            this.props.onTextareaFocus();
            this.embeddedState.languageId = languageId;
            this.openCodeToolbar();
        }
    }
}

export const syntaxHighlightingEmbedding = {
    name: "syntaxHighlighting",
    Component: EmbeddedSyntaxHighlightingComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) => new StateChangeManager(config),
};
