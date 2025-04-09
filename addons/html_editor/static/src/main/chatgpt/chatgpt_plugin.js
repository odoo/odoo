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
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
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

    /**
     * Converts record data to JSON, so we can pass them to the AI record's context
     * @returns {String} String JSON representation of the record
     */
    recordDataToJSON(recordData, fieldsInfo) {
        const result = {};

        for (const fieldName in recordData) {
            if (!recordData.hasOwnProperty(fieldName)) continue;
            const fieldValue = recordData[fieldName];
            const fieldInfo = fieldsInfo[fieldName] || {};
            // Skip binary fields entirely - there is no easy way of placing them in the context
            if (fieldInfo.type === 'binary') {
                continue;
            }
            // Handle relational fields
            if (['many2one', 'many2many', 'one2many'].includes(fieldInfo.type)) {
                // Skip abnormally large relational fields which can floud the AI context
                if (fieldValue && fieldValue.records && fieldValue.records.length > 50) {
                    continue;
                }
                switch (fieldInfo.type) {
                    case 'many2one':
                        result[fieldName] = fieldValue ? fieldValue.display_name || fieldValue.name : null;
                        break;
                    case 'many2many':
                    case 'one2many':
                        if (fieldValue && fieldValue.records) {
                            result[fieldName] = fieldValue.records.map(record => 
                                record.data.display_name || record.data.name
                            );
                        } else {
                            result[fieldName] = [];
                        }
                        break;
                }
            } else if (fieldInfo.type === 'date' && fieldValue) {  // handle date fields
                const date = luxon.DateTime.fromISO(fieldValue);
                result[fieldName] = date.isValid ? formatDate(date) : fieldValue;
            } else if (fieldInfo.type === 'datetime' && fieldValue) {  // handle datetime fields
                const datetime = luxon.DateTime.fromISO(fieldValue);
                result[fieldName] = datetime.isValid ? formatDateTime(datetime) : fieldValue;
            } else {  // handle all other types of fields
                result[fieldName] = fieldValue;
            }
        }
        return result;
    }

    async openDialog(params = {}) {
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
            let recordModel, recordName, recordId, callerId, placeholderPrompt, callerComp, textSelection, frontEndRecordInfo;
            // fetch record information that we need for the channel creation
            const { resModel, resId, data, fields, id } = this.config.getRecordInfo();
            const recordInfoJSON = this.recordDataToJSON(data, fields);
            if (selection.isCollapsed) {
                if (resModel === "mail.compose.message") {
                    callerComp = "html_field_composer";
                    recordName = data.record_name;
                    recordModel = data.model;
                    recordId = Number(data.res_ids.slice(1,-1));
                    placeholderPrompt = 'Write a follow up answer';
                    callerId = id;
                } else {
                    callerComp = "html_field_record";
                    recordName = recordInfoJSON.name;
                    recordModel = resModel;
                    placeholderPrompt = "";
                    frontEndRecordInfo = JSON.stringify(recordInfoJSON);
                    // set insertButtonCaller flag to the record's id
                    callerId = resId || id;
                    this.services['mail.store']["mail.message"].insertButtonCaller = resId || id;
                }
            } else {
                callerComp = "html_field_text_select";
                recordName = data.record_name || recordInfoJSON.name;
                placeholderPrompt = "Rewrite";
                textSelection = selection.textContent();
                // set insertButtonCaller flag to the records id
                callerId = resId || id;
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
                    frontEndRecordInfo,
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
