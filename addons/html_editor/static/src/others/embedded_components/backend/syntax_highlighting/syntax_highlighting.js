/* global Prism */
import {
    applyObjectPropertyDifference,
    getEmbeddedProps,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import { Component, onMounted, useEffect, useRef, useState, onWillDestroy } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { newlinesToLineBreaks } from "../../plugins/syntax_highlighting_plugin/syntax_highlighting_plugin";
import { cookie } from "@web/core/browser/cookie";

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
export const DEFAULT_LANGUAGE_ID = "plaintext";

export class EmbeddedSyntaxHighlightingComponent extends Component {
    static template = "html_editor.EmbeddedSyntaxHighlighting";

    static props = {
        initialValue: { type: String },
        autofocus: { type: Boolean },
        codeToolbar: { type: Object },
        onTextareaFocus: { type: Function },
        addHistoryStep: { type: Function },
        getPreValue: { type: Function },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.loadPrism();
        this.state = useState({
            isActive: false,
            host: this.props.host,
        });
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

            // Set the initial values and highlight the pre.
            this.initialValue =
                this.state.host.dataset.syntaxHighlightingValue || this.props.initialValue;
            this.initialLanguageId = this.state.host.dataset.languageId || DEFAULT_LANGUAGE_ID;
            this.commitToHost(
                {
                    value: this.initialValue,
                    languageId: this.initialLanguageId,
                },
                false
            ).then((didHighlight) => !didHighlight && this.highlight());

            // Ensure the values of the dataset and the content match.
            this.observer = new MutationObserver((mutations) => {
                if (mutations.some((mutation) => mutation.oldValue !== null)) {
                    // Prevent UNDO from returning to a state where the dataset
                    // was not yet defined.
                    if (!("syntaxHighlightingValue" in this.state.host.dataset)) {
                        this.state.host.dataset.syntaxHighlightingValue = this.initialValue;
                    }
                    if (!("languageId" in this.state.host.dataset)) {
                        this.state.host.dataset.languageId = this.initialLanguageId;
                    }
                    this.highlight();
                }
            });
            this.observer.observe(this.state.host, {
                attributeFilter: ["data-syntax-highlighting-value", "data-language-id"],
                attributeOldValue: true,
            });
        });
        onWillDestroy(() => {
            this.observer?.disconnect();
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
    }

    /**
     * Load the Prism library. This function exists only so it can be overridden
     * in tests.
     */
    loadPrism() {
        return loadBundle("html_editor.assets_prism");
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

    /**
     * Set the value and/or the language ID in the host's dataset so they can be
     * saved. If anything changed, highlight the pre and add a history step
     * (unless `addStep` is false).
     *
     * @param {{ value?: string, languageId?: string }} values
     * @param {boolean} [addStep = true]
     * @returns {Promise<boolean>} true if anything changed.
     */
    async commitToHost(values, addStep = true) {
        let hasChanged = false;
        if ("value" in values && this.state.host.dataset.syntaxHighlightingValue !== values.value) {
            hasChanged = true;
            this.state.host.dataset.syntaxHighlightingValue = values.value;
        }
        if ("languageId" in values && this.state.host.dataset.languageId !== values.languageId) {
            hasChanged = true;
            this.state.host.dataset.languageId = values.languageId;
        }
        if (hasChanged) {
            await this.highlight();
            if (addStep) {
                this.props.addHistoryStep();
            }
        }
        return hasChanged;
    }

    /**
     * Get the saved value or language ID from the host's dataset.
     *
     * @param {"value" | "languageId"} key
     * @returns {string | undefined}
     */
    getFromHostDataset(key) {
        return this.state.host.dataset[key == "value" ? "syntaxHighlightingValue" : key];
    }

    /**
     * Use the Prism library to highlight the pre using the value and language
     * stored on the host's dataset. Ensure the values (pre, host, textarea)
     * match and commit the value if it changed in the process.
     *
     * @param {boolean} [focus = this.document.activeElement === this.textarea]
     */
    async highlight(focus = this.document.activeElement === this.textarea) {
        if (!window.Prism) {
            await this.loadPrism();
            if (!window.Prism) {
                console.error("The Prism library couldn't be found.");
                return;
            }
        }
        const languageId = this.getFromHostDataset("languageId");
        // We need a temporary element because directly changing the HTML of the
        // PRE, or using replaceChildren both mess up the history by not
        // recording the removal of the contents.
        const fakeElement = this.document.createElement("pre");
        fakeElement.innerHTML = Prism.highlight(
            this.getFromHostDataset("value"),
            Prism.languages[languageId],
            languageId
        );

        // Post-process highlighted HTML.
        newlinesToLineBreaks(fakeElement, this.document);

        // Replace the PRE's contents with the highlighted ones.
        [...this.pre.childNodes].forEach((child) => child.remove());
        [...fakeElement.childNodes].forEach((child) => this.pre.append(child));

        // Ensure the values match.
        const preValue = this.props.getPreValue(this.pre);
        if (this.textarea.value !== preValue) {
            this.textarea.value = preValue;
        }
        if (focus) {
            this.textarea.focus({ preventScroll: true });
            this.props.onTextareaFocus();
        }
        await this.commitToHost({ value: this.textarea.value });
    }

    onInput() {
        this.textarea.focus();
        this.props.onTextareaFocus();
        this.commitToHost({ value: this.textarea.value });
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
            this.commitToHost({ value: this.textarea.value });
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
        if (this.getFromHostDataset("languageId") !== languageId) {
            this.props.codeToolbar.close();
            this.textarea.focus();
            this.props.onTextareaFocus();
            this.commitToHost({ languageId }).then(() => {
                this.openCodeToolbar();
            });
        }
    }
}

export const syntaxHighlightingEmbedding = {
    name: "syntaxHighlighting",
    Component: EmbeddedSyntaxHighlightingComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                propertyUpdater: {
                    value: (state, previous, next) => {
                        applyObjectPropertyDifference(state, "value", previous.value, next.value);
                    },
                },
            })
        ),
};
