import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "../../utils/dom_traversal";
import { createDocumentFragmentFromContent } from "@mail/utils/common/html";
import { ChatGPTTranslateDialog } from "./chatgpt_translate_dialog";
import { LanguageSelector } from "./language_selector";
import { withSequence } from "@html_editor/utils/resource";
import { user } from "@web/core/user";
import { isContentEditable } from "@html_editor/utils/dom_info";
import { unwrapContents } from "../../utils/dom";

export class ChatGPTPlugin extends Plugin {
    static id = "chatgpt";
    static dependencies = [
        "baseContainer",
        "selection",
        "history",
        "dom",
        "sanitize",
        "dialog",
        "split",
    ];
    resources = {
        user_commands: [
            {
                id: "openChatGPTDialog",
                title: _t("ChatGPT"),
                description: _t("Generate or transform content with AI"),
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
                description: _t("Translate with AI"),
                isAvailable: (selection) => {
                    return !selection.isCollapsed && user.userId;
                },
                isDisabled: this.isNotReplaceableByAI.bind(this),
                Component: LanguageSelector,
                props: {
                    onSelected: (language) => this.openDialog({ language }),
                    isDisabled: (selection) => {
                        return this.isNotReplaceableByAI(selection);
                    },
                },
            },
            {
                id: "chatgpt",
                groupId: "ai",
                commandId: "openChatGPTDialog",
                text: "AI",
                namespaces: ["compact", "expanded"],
                isDisabled: this.isNotReplaceableByAI.bind(this),
            },
        ],

        powerbox_categories: withSequence(70, { id: "ai", name: _t("AI Tools") }),
        powerbox_items: {
            keywords: [_t("AI")],
            categoryId: "ai",
            commandId: "openChatGPTDialog",
            icon: "fa-magic",
            // isAvailable: () => !this.odooEditor.isSelectionInBlockRoot(), // TODO!
        },

        power_buttons: withSequence(20, {
            commandId: "openChatGPTDialog",
            text: "AI",
        }),
    };

    isNotReplaceableByAI(selection = this.dependencies.selection.getEditableSelection()) {
        const isEmpty = !selection.textContent().replace(/\s+/g, "");
        const cannotReplace = this.dependencies.selection
            .getTraversedNodes()
            .find((el) => this.dependencies.split.isUnsplittable(el) || !isContentEditable(el));
        return cannotReplace || isEmpty;
    }

    async openDialog(params = {}) {
        // Force save the record before opening the AI dialog
        // This ensures up-to-date info for the model + prevents launching the dialog with an empty record.
        const saved = await this.config.onAICommandSave();
        if (!saved){
            return;
        }
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
                unwrapContents(insertedNodes[0]);
            },
            ...params,
        };
        dialogParams.baseContainer = this.dependencies.baseContainer.getDefaultNodeName();
        // collapse to end
        const sanitize = this.dependencies.sanitize.sanitize;
        if (params.language) {
            const originalText = selection.textContent() || "";
            this.dependencies.dialog.addDialog(
                ChatGPTTranslateDialog,
                { ...dialogParams, originalText, sanitize }
            );
        } else {
            let recordModel, recordName, recordId, callerId, placeholderPrompt, callerComp, textSelection;
            // fetch record information that we need for the channel creation
            const { resModel, resId, data, id } = this.config.getRecordInfo();
            if (selection.isCollapsed) {
                if (resModel !== "mail.compose.message") {
                    const resultName = await this.services.orm.read(resModel, [ resId ], [ 'name' ]);
                    recordName = resultName[0]['name'];
                    recordModel = resModel;
                    recordId = callerId = resId;
                    callerComp = "html_field_record";
                    placeholderPrompt = "";
                    // set insertButtonCaller flag to the records id
                    this.services['mail.store']["mail.message"].insertButtonCaller = resId;
                } else {
                    recordName = data.record_name;
                    recordModel = data.model;
                    recordId = Number(data.res_ids.slice(1,-1));
                    callerComp = "html_field_composer";
                    callerId = id;
                    placeholderPrompt = 'Write a follow up answer';
                }
            } else {
                callerComp = "html_field_text_select";
                recordName = data.record_name
                if (!recordName) {
                    const temp_name = await this.services.orm.read(resModel, [ resId ], [ 'name' ]);
                    recordName = temp_name[0]['name'];
                }
                placeholderPrompt = "Rewrite";
                textSelection = selection.textContent();
                callerId = resId || id;
                // set insertButtonCaller flag to the records id
                this.services['mail.store']["mail.message"].insertButtonCaller = resId || id;
            }
            // create the discuss channel used for talking with the ai
            const ai_channel_id = await this.services.orm.call(
                'discuss.channel',
                'create_ai_composer_channel',
                [ 
                    callerComp,
                    recordName,
                    recordModel,
                    recordId,
                    textSelection,
                ], 
            );
            // create and open the thread for the discuss channel
            const thread = await this.services['mail.store'].Thread.getOrFetch({
                model: "discuss.channel",
                id: Number(ai_channel_id), 
            });
            thread.open({ 
                focus: true, 
                specialActions: {
                    'insert': dialogParams.insert,
                },
                chatCaller: callerId,
                composerText: placeholderPrompt,
            });
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
