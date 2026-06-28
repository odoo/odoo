import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { Component, onWillStart, signal, useEffect, types as t } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import {
    getPreValue,
    highlightPre,
} from "../../core/syntax_highlighting/syntax_highlighting_utils";
import { CodeToolbar } from "./code_toolbar";
import { nodeSize } from "@html_editor/utils/position";

export class EmbeddedSyntaxHighlightingComponent extends Component {
    static template = "html_editor.EmbeddedSyntaxHighlighting";

    static components = { CodeToolbar };
    static props = {
        value: { type: String },
        languageId: { type: String },
        codeWrap: { type: Boolean, optional: true },
        onTextareaFocus: { type: Function },
        convertToParagraph: { type: Function },
        setSelection: { type: Function },
        host: { type: Object },
    };

    highlightedValue = signal("");
    preRef = signal(null, { type: t.ref() });
    textareaRef = signal(null, { type: t.ref() });

    setup() {
        super.setup();
        this.embeddedState = useEmbeddedState(this.props.host);

        onWillStart(() => this.loadPrism());

        useEffect(() => {
            if (this.textareaRef()) {
                this.document = this.textareaRef().ownerDocument;
                this.highlight();
            }
        });
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
        const focus = this.document.activeElement === this.textareaRef();

        highlightPre(this.preRef(), this.embeddedState.value, this.embeddedState.languageId);

        // Ensure the values match.
        const preValue = getPreValue(this.preRef());
        if (this.textareaRef().value !== preValue) {
            this.textareaRef().value = preValue;
        }
        if (focus) {
            this.textareaRef().focus({ preventScroll: true });
            this.props.onTextareaFocus();
        }
        this.embeddedState.value = this.textareaRef().value;
    }

    onInput() {
        this.textareaRef().focus();
        this.props.onTextareaFocus();
        this.embeddedState.value = this.textareaRef().value;
    }

    /**
     * Handle tabulation in the textarea.
     *
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (ev.key === "Tab") {
            ev.preventDefault();
            const tabSize = +getComputedStyle(this.textareaRef()).tabSize || 4;
            const tab = " ".repeat(tabSize);
            const { selectionStart, selectionEnd } = this.textareaRef();
            const collapsed = selectionStart === selectionEnd;
            let start = this.textareaRef().value.slice(0, selectionStart).lastIndexOf("\n");
            start = start === -1 ? 0 : start;
            let newValue = "";
            let spacesRemovedAtStart = 0;
            if (ev.shiftKey) {
                // Remove tabs.
                let end = this.textareaRef()
                    .value.slice(selectionEnd, this.textareaRef().value.length)
                    .indexOf("\n");
                end = end === -1 ? 0 : end;
                end = selectionEnd + end;
                // From 0 to the last \n before selection start.
                newValue = this.textareaRef().value.slice(0, start);
                // From the last \n before selection start to selection end.
                const regex = new RegExp(`(\n|^)( |\u00A0){1,${tabSize}}`, "g");
                const startSlice = this.textareaRef().value.slice(start, selectionStart);
                const cleanStartSlice = startSlice.replace(regex, "$1");
                spacesRemovedAtStart = startSlice.length - cleanStartSlice.length;
                newValue += cleanStartSlice;
                newValue += this.textareaRef()
                    .value.slice(selectionStart, selectionEnd)
                    .replace(regex, "$1");
                newValue += this.textareaRef().value.slice(selectionEnd, end).replace(regex, "$1");
                // From selection end to end.
                newValue += this.textareaRef().value.slice(end, this.textareaRef().value.length);
            } else {
                // Insert tabs.
                if (collapsed && /\S/.test(this.textareaRef().value.slice(start, selectionStart))) {
                    newValue =
                        this.textareaRef().value.slice(0, selectionStart) +
                        tab +
                        this.textareaRef().value.slice(
                            selectionStart,
                            this.textareaRef().value.length
                        );
                } else {
                    // From 0 to the last \n before selection start.
                    newValue = start ? this.textareaRef().value.slice(0, start) : tab;
                    // From the last \n before selection start to selection end.
                    newValue += this.textareaRef()
                        .value.slice(start, selectionEnd)
                        .replaceAll("\n", `\n${tab}`);
                    // From selection end to end.
                    newValue += this.textareaRef().value.slice(
                        selectionEnd,
                        this.textareaRef().value.length
                    );
                }
            }
            const insertedChars = newValue.length - this.textareaRef().value.length;
            this.textareaRef().value = newValue;
            const newStart = selectionStart + (ev.shiftKey ? -spacesRemovedAtStart : tabSize);
            const newEnd = collapsed ? newStart : selectionEnd + insertedChars;
            this.textareaRef().setSelectionRange(
                newStart,
                newEnd,
                this.textareaRef().selectionDirection
            );
            this.embeddedState.value = this.textareaRef().value;
        } else if (ev.key === "Backspace") {
            // Transform empty code block into base container on backspace.
            if (this.textareaRef().value === "") {
                ev.preventDefault();
                this.props.convertToParagraph({ target: this.preRef() });
            }
        } else if (ev.key === "ArrowUp" || ev.key === "ArrowDown") {
            const { value, selectionStart, selectionEnd } = this.textareaRef();
            if (selectionStart !== selectionEnd) {
                return;
            }
            const isArrowUp = ev.key === "ArrowUp";
            const isCursorAtBoundary = isArrowUp
                ? value.slice(0, selectionStart).lastIndexOf("\n") === -1
                : value.indexOf("\n", selectionEnd) === -1;
            if (!isCursorAtBoundary) {
                return;
            }
            ev.preventDefault();
            this.textareaRef().blur();
            const node = isArrowUp
                ? this.props.host.previousElementSibling
                : this.props.host.nextElementSibling;
            this.props.setSelection({
                anchorNode: node,
                anchorOffset: isArrowUp ? nodeSize(node) : 0,
            });
        }
    }

    /**
     * Ensure the pre and textarea's scrolls match so they remain aligned.
     */
    onScroll() {
        this.preRef().scrollTop = this.textareaRef().scrollTop;
        this.preRef().scrollLeft = this.textareaRef().scrollLeft;
    }

    /**
     * Change the language when selecting a new one via the code toolbar.
     *
     * @param {string} languageId
     */
    onLanguageChange(languageId) {
        if (languageId && this.embeddedState.languageId !== languageId) {
            this.textareaRef().focus();
            this.props.onTextareaFocus();
            this.embeddedState.languageId = languageId;
        }
    }

    /**
     * Toggles content wrapping via the code toolbar.
     */
    toggleCodeWrap() {
        if (Object.hasOwn(this.embeddedState, "codeWrap")) {
            delete this.embeddedState.codeWrap;
        } else {
            this.embeddedState.codeWrap = true;
        }
        this.props.host.classList.toggle("o-code-wrap", this.embeddedState.codeWrap);
    }
}

export const syntaxHighlightingEmbedding = {
    name: "syntaxHighlighting",
    Component: EmbeddedSyntaxHighlightingComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) => new StateChangeManager(config),
};
