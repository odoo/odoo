import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "../../utils/dom_traversal";
import { ChatGPTPromptDialog } from "./chatgpt_prompt_dialog";
import { ChatGPTAlternativesDialog } from "./chatgpt_alternatives_dialog";
import { ChatGPTTranslateDialog } from "./chatgpt_translate_dialog";
import { LanguageSelector } from "./language_selector";

export class ChatGPTPlugin extends Plugin {
    static name = "chatgpt";
    static dependencies = ["selection", "history", "dom", "sanitize"];
    static resources = (p) => ({
        toolbarCategory: {
            id: "ai",
            sequence: 50,
        },
        toolbarItems: [
            {
                id: "translate",
                category: "ai",
                Component: LanguageSelector,
                props: { dispatch: p.dispatch },
            },
            {
                id: "chatgpt",
                category: "ai",
                action(dispatch) {
                    dispatch("OPEN_CHATGPT_DIALOG");
                },
                icon: "fa-magic",
                name: "chatgpt",
                label: _t("Generate or transform content with AI."),
                text: "AI",
            },
        ],

        powerboxCategory: { id: "ai", name: _t("AI Tools"), sequence: 70 },
        powerboxItems: {
            name: _t("ChatGPT"),
            description: _t("Generate or transform content with AI."),
            category: "ai",
            fontawesome: "fa-magic",
            action(dispatch) {
                dispatch("OPEN_CHATGPT_DIALOG");
            },
            // isAvailable: () => !this.odooEditor.isSelectionInBlockRoot(), // TODO!
        },
    });

    handleCommand(command, payload) {
        switch (command) {
            case "OPEN_CHATGPT_DIALOG": {
                this.openDialog(payload);
                break;
            }
        }
    }

    openDialog(params = {}) {
        const selection = this.shared.getEditableSelection();
        const cursors = this.shared.preserveSelection();
        const onClose = cursors.restore;
        const dialogParams = {
            insert: (content) => {
                const insertedNodes = this.shared.domInsert(content);
                this.dispatch("ADD_STEP");
                // Add a frame around the inserted content to highlight it for 2
                // seconds.
                const start = insertedNodes?.length && closestElement(insertedNodes[0]);
                const end =
                    insertedNodes?.length &&
                    closestElement(insertedNodes[insertedNodes.length - 1]);
                if (start && end) {
                    const divContainer = this.editable.parentElement;
                    let [parent, left, top] = [
                        start.offsetParent,
                        start.offsetLeft,
                        start.offsetTop - start.scrollTop,
                    ];
                    while (parent && !parent.contains(divContainer)) {
                        left += parent.offsetLeft;
                        top += parent.offsetTop - parent.scrollTop;
                        parent = parent.offsetParent;
                    }
                    let [endParent, endTop] = [end.offsetParent, end.offsetTop - end.scrollTop];
                    while (endParent && !endParent.contains(divContainer)) {
                        endTop += endParent.offsetTop - endParent.scrollTop;
                        endParent = endParent.offsetParent;
                    }
                    const div = document.createElement("div");
                    div.classList.add("o-chatgpt-content");
                    const FRAME_PADDING = 3;
                    div.style.left = `${left - FRAME_PADDING}px`;
                    div.style.top = `${top - FRAME_PADDING}px`;
                    div.style.width = `${
                        Math.max(start.offsetWidth, end.offsetWidth) + FRAME_PADDING * 2
                    }px`;
                    div.style.height = `${endTop + end.offsetHeight - top + FRAME_PADDING * 2}px`;
                    divContainer.prepend(div);
                    setTimeout(() => div.remove(), 2000);
                }
            },
            ...params,
        };
        // collapse to end
        const sanitize = this.shared.sanitize;
        if (selection.isCollapsed) {
            this.services.dialog.add(
                ChatGPTPromptDialog,
                { ...dialogParams, sanitize },
                { onClose }
            );
        } else {
            const range = new Range();
            range.setStart(selection.startContainer, selection.startOffset);
            range.setEnd(selection.endContainer, selection.endOffset);
            const originalText = range.toString() || "";
            this.services.dialog.add(
                params.language ? ChatGPTTranslateDialog : ChatGPTAlternativesDialog,
                { ...dialogParams, originalText, sanitize },
                { onClose }
            );
        }
    }
}
