import { Plugin } from "@html_editor/plugin";
import { loadBundle } from "@web/core/assets";
import { CodeToolbar } from "./code_toolbar";
import { xml } from "@odoo/owl";
import { renderToElement } from "@web/core/utils/render";

const LANGUAGES = [
    { displayName: "Plain Text", id: "plaintext", default: true },
    { displayName: "Markdown", id: "markdown" },
    { displayName: "Javascript", id: "javascript" },
    { displayName: "Typescript", id: "typescript" },
    { displayName: "JSDoc", id: "jsdoc" },
    { displayName: "Java", id: "java" },
    { displayName: "Python", id: "python" },
    { displayName: "HTML", id: "html" },
    { displayName: "XML", id: "xml" },
    { displayName: "SVG", id: "svg" },
    { displayName: "JSON", id: "json" },
    { displayName: "CSS", id: "css" },
    { displayName: "SASS", id: "sass" },
    { displayName: "SCSS", id: "scss" },
    { displayName: "SQL", id: "sql" },
    { displayName: "Diff", id: "diff" },
];
const DEFAULT_LANGUAGE = LANGUAGES.find((language) => language.default);

export class SyntaxHighlightingPlugin extends Plugin {
    static id = "syntaxHighlighting";
    static dependencies = ["overlay", "history", "selection", "protectedNode"];
    resources = {
        normalize_handlers: (root) => this.prepareCodeBlocks(root, true),
        post_undo_handlers: () => {
            this.prepareCodeBlocks(this.editable, true);
        },
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.codeToolbar = this.dependencies.overlay.createOverlay(CodeToolbar, {
            positionOptions: {
                position: "top-fit",
                flip: false,
            },
            closeOnPointerdown: false,
        });
        this.addGlobalDomListener("pointermove", this.onMouseMove);
        this.addGlobalDomListener("click", this.onMouseMove);
        this.addDomListener(this.document, "scroll", this.codeToolbar.close, true);
        this.prepareCodeBlocks();
        const pres = this.editable.querySelectorAll("pre");
        if (pres.length) {
            this.loadPrism();
        }
    }

    destroy() {
        for (const codeBlock of this.editable.querySelectorAll("div.o_syntax_highlighting")) {
            this.removeListeners(codeBlock);
        }
    }

    prepareCodeBlocks(root = this.editable, activate = false) {
        let activeTextarea =
            this.document.activeElement.nodeName === "TEXTAREA" && this.document.activeElement;
        const textareaSelection = {
            start: activeTextarea?.selectionStart || 0,
            end: activeTextarea?.selectionEnd || 0,
            direction: activeTextarea?.selectionDirection || "forward",
        };
        for (const pre of root.querySelectorAll("pre")) {
            if (!pre.closest("div.o_syntax_highlighting")) {
                const font = getComputedStyle(pre).font.replaceAll('"', "'");
                const div = renderToElement(
                    xml`<div class="o_syntax_highlighting" data-language-id="${DEFAULT_LANGUAGE.id}" style="font: ${font};"/>`
                );
                pre.before(div);
                div.append(pre);
            }
        }
        for (const codeBlock of this.editable.querySelectorAll("div.o_syntax_highlighting")) {
            this.dependencies.protectedNode.setProtectingNode(codeBlock, true);
            const pre = codeBlock.querySelector("pre");
            const preStyle = getComputedStyle(pre);
            let textarea = codeBlock.querySelector("textarea.o_prism_source");
            if (!textarea) {
                textarea = renderToElement(
                    xml`<textarea class="o_prism_source" contenteditable="true"
                        style="padding: ${preStyle.padding}; margin: ${preStyle.margin};"/>`
                );
                codeBlock.append(textarea);
                activeTextarea = activate && textarea; // It's the latest inserted one.
            }
            // Trailing br gives \n in innerText but should not be visible.
            const trailingBrs = pre.innerHTML.match(/(<br>)+$/)?.length || 0;
            const preInnerText = pre.innerText.slice(
                0,
                pre.innerText.length - (trailingBrs > 1 ? trailingBrs - 1 : trailingBrs)
            );
            if (textarea.value !== preInnerText) {
                textarea.value = preInnerText;
            }
            this.resetListeners(codeBlock);
        }
        if (activeTextarea) {
            if (activate) {
                this.setActiveCodeBlock(activeTextarea.parentElement);
            }
            setTimeout(
                () =>
                    activeTextarea.setSelectionRange(
                        textareaSelection.start,
                        textareaSelection.end,
                        textareaSelection.direction
                    ),
                10
            );
        }
    }

    removeListeners(codeBlock) {
        const textarea = codeBlock.querySelector("textarea");
        codeBlock.removeEventListener("input", this.boundOnCodeBlockInput);
        codeBlock.removeEventListener("keydown", this.boundOnCodeBlockKeydown);
        textarea.removeEventListener("scroll", this.boundOnTextareaScroll);
    }

    resetListeners(codeBlock) {
        this.boundOnCodeBlockInput ||= this.onCodeBlockInput.bind(this);
        this.boundOnCodeBlockKeydown ||= this.onCodeBlockKeydown.bind(this);
        this.boundOnTextareaScroll ||= this.onTextareaScroll.bind(this);

        this.removeListeners(codeBlock);
        const textarea = codeBlock.querySelector("textarea");
        codeBlock.addEventListener("input", this.boundOnCodeBlockInput);
        codeBlock.addEventListener("keydown", this.boundOnCodeBlockKeydown);
        textarea.addEventListener("scroll", this.boundOnTextareaScroll);
    }

    async loadPrism() {
        this.prismPromise = loadBundle("html_editor.assets_prism");
        return this.prismPromise.then(() => {
            this.Prism = window.top.Prism;
            this.Prism.manual = true;
            this.prismPromise = undefined;
        });
    }

    onCodeBlockInput(ev) {
        this.highlight(ev.currentTarget);
    }

    onCodeBlockKeydown(ev) {
        if (ev.key === "Tab") {
            ev.preventDefault();
            const textarea = ev.currentTarget.querySelector("textarea");
            const tabSize = +getComputedStyle(textarea).tabSize || 4;
            const tab = new Array(tabSize + 1).join(" ");
            const { selectionStart, selectionEnd } = textarea;
            const collapsed = selectionStart === selectionEnd;
            let start = [...textarea.value.slice(0, selectionStart)].findLastIndex(
                (char) => char === "\n"
            );
            start = start === -1 ? 0 : start;
            let newValue = "";
            let spacesRemovedAtStart = 0;
            if (ev.shiftKey) {
                // Remove tabs.
                let end = [...textarea.value.slice(selectionEnd, textarea.value.length)].findIndex(
                    (char) => char === "\n"
                );
                end = end === -1 ? 0 : end;
                end = selectionEnd + end;
                // From 0 to the last \n before selection start.
                newValue = textarea.value.slice(0, start);
                // From the last \n before selection start to selection end.
                const regex = new RegExp(`(\n|^)( |\u00A0){1,${tabSize}}`, "g");
                newValue += textarea.value.slice(start, selectionEnd).replace(regex, "$1");
                spacesRemovedAtStart = selectionEnd - newValue.length;
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
            this.highlight(ev.currentTarget);
            textarea.setSelectionRange(newStart, newEnd, textarea.selectionDirection);
        }
    }

    onTextareaScroll(ev) {
        const textarea = ev.currentTarget;
        const pre = textarea.parentElement.querySelector("pre");
        pre.scrollTop = textarea.scrollTop;
        pre.scrollLeft = textarea.scrollLeft;
    }

    onMouseMove(ev) {
        const codeBlock = ev.target.closest?.(".o_syntax_highlighting");
        const isLanguageSelectorOpen = !!this.document.querySelector(
            ".dropdown-menu.o_language_selector"
        );
        if (isLanguageSelectorOpen) {
            return;
        }
        if (codeBlock && codeBlock !== this.activeCodeBlock && this.editable.contains(codeBlock)) {
            this.setActiveCodeBlock(codeBlock);
        } else if (this.activeCodeBlock) {
            const isOverlay = !!ev.target.closest(".o-overlay-container");
            if (isOverlay) {
                return;
            }
            if (!codeBlock) {
                this.setActiveCodeBlock(null);
            }
        }
    }

    onLanguageChange(codeBlock, languageId) {
        if (codeBlock.dataset.languageId !== languageId) {
            codeBlock.dataset.languageId = languageId;
            this.highlight(codeBlock);
        }
    }

    async highlight(codeBlock) {
        if (!this.Prism) {
            await (this.prismPromise || this.loadPrism());
        }
        const pre = codeBlock.querySelector("pre");
        const textarea = codeBlock.querySelector("textarea.o_prism_source");
        const languageId = codeBlock.dataset.languageId || DEFAULT_LANGUAGE.id;
        const html = this.Prism.highlight(
            textarea.value,
            this.Prism.languages[languageId] || this.Prism.languages[DEFAULT_LANGUAGE.id],
            languageId || DEFAULT_LANGUAGE.id
        )
            // Handle trailing BRs. Eg, <span>ab\n</span> -> <span>ab</span><br><br>
            .replace(/(\n+)((<\/[^>]+>)*)$/, "$2\n$1")
            .replaceAll("\n", "<br>");
        // Make sure the step is properly recorded to include the code block's
        // data attribute and the PRE's content.
        this.dependencies.protectedNode.setProtectingNode(codeBlock, false);
        // Render and replace the PRE's contents.
        const fakeElement = this.document.createElement("fake-element");
        fakeElement.innerHTML = html || "<br>";
        for (const child of [...pre.childNodes]) {
            child.remove();
        }
        for (const child of [...fakeElement.childNodes]) {
            pre.append(child);
        }
        this.dependencies.history.addStep();
        this.dependencies.protectedNode.setProtectingNode(codeBlock, true); // actually not needed because done in normalize handler
        textarea.focus({ preventScroll: true });
    }

    setActiveCodeBlock(codeBlock) {
        this.activeCodeBlock = codeBlock;
        this.codeToolbar.close();
        if (codeBlock) {
            this.codeToolbar.open({
                target: codeBlock,
                props: {
                    target: codeBlock,
                    prismSource: codeBlock.querySelector("textarea"),
                    languages: LANGUAGES,
                    onLanguageChange: this.onLanguageChange.bind(this),
                },
            });
            codeBlock.querySelector("textarea").focus();
        }
    }
}
