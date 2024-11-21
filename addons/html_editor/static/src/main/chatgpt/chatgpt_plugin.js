import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "../../utils/dom_traversal";
import { ChatGPTPromptDialog } from "./chatgpt_prompt_dialog";
import { ChatGPTAlternativesDialog } from "./chatgpt_alternatives_dialog";
import { ChatGPTTranslateDialog } from "./chatgpt_translate_dialog";
import { LanguageSelector } from "./language_selector";
import { withSequence } from "@html_editor/utils/resource";
import { user } from "@web/core/user";

export class ChatGPTPlugin extends Plugin {
    static id = "chatgpt";
    static dependencies = ["selection", "history", "dom", "sanitize", "dialog"];
    resources = {
        user_commands: [
            {
                id: "openChatGPTDialog",
                title: _t("ChatGPT"),
                description: _t("Generate or transform content with AI."),
                icon: "fa-magic",
                run: this.openDialog.bind(this),
            },
        ],
        toolbar_groups: withSequence(50, {
            id: "ai",
        }),
        toolbar_items: [
            {
                id: "translate",
                groupId: "ai",
                title: _t("Translate with AI"),
                isAvailable: (selection) => {
                    return !selection.isCollapsed && user.userId;
                },
                Component: LanguageSelector,
                props: {
                    onSelected: (language) => this.openDialog({ language }),
                },
            },
            {
                id: "chatgpt",
                groupId: "ai",
                commandId: "openChatGPTDialog",
                text: "AI",
            },
        ],

        powerbox_categories: withSequence(70, { id: "ai", name: _t("AI Tools") }),
        powerbox_items: {
            keywords: [_t("AI")],
            categoryId: "ai",
            commandId: "openChatGPTDialog",
            // isAvailable: () => !this.odooEditor.isSelectionInBlockRoot(), // TODO!
        },
    };

    openDialog(params = {}) {
        const selection = this.dependencies.selection.getEditableSelection();
        const dialogParams = {
            insert: (content) => {
                const insertedNodes = this.dependencies.dom.insert(content);
                this.dependencies.history.addStep();
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
        const sanitize = this.dependencies.sanitize.sanitize;
        if (selection.isCollapsed) {
            this.dependencies.dialog.addDialog(ChatGPTPromptDialog, { ...dialogParams, sanitize });
        } else {
            const originalText = selection.textContent() || "";
            this.dependencies.dialog.addDialog(
                params.language ? ChatGPTTranslateDialog : ChatGPTAlternativesDialog,
                { ...dialogParams, originalText, sanitize }
            );
        }
        if (this.services.ui.isSmall) {
            // TODO: Find a better way and avoid modifying range
            // HACK: In the case of opening through dropdown:
            // - when dropdown open, it keep the element focused before the open
            // - when opening the dialog through the dropdown, the dropdown closes
            // - upon close, the generic code of the dropdown sets focus on the kept element (in our case, the editable)
            // - we need to remove the range after the generic code of the dropdown is triggered so we hack it by removing the range in the next tick
            Promise.resolve().then(() => {
                // If the dialog is opened on a small screen, remove all selection
                // because the selection can be seen through the dialog on some devices.
                this.document.getSelection()?.removeAllRanges();
            });
        }
    }
}
