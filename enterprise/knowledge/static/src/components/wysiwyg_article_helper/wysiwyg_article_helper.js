import { Component, onWillStart } from "@odoo/owl";
import { ChatGPTPromptDialog } from "@html_editor/main/chatgpt/chatgpt_prompt_dialog";
import { parseHTML } from "@html_editor/utils/html";
import { ArticleTemplatePickerDialog } from "@knowledge/components/article_template_picker_dialog/article_template_picker_dialog";
import { ItemCalendarPropsDialog } from "@knowledge/components/item_calendar_props_dialog/item_calendar_props_dialog";
import { PromptEmbeddedViewNameDialog } from "@knowledge/components/prompt_embedded_view_name_dialog/prompt_embedded_view_name_dialog";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { renderToFragment } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";

export class WysiwygArticleHelper extends Component {
    static template = "knowledge.WysiwygArticleHelper";
    static props = {
        editor: { type: Object },
        isVisible: { type: Boolean },
        record: { type: Object },
    };

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        onWillStart(async () => {
            this.isPortalUser = await user.hasGroup("base.group_portal");
        });
    }

    onLoadTemplateBtnClick() {
        this.dialogService.add(ArticleTemplatePickerDialog, {
            onLoadTemplate: async (articleTemplateId) => {
                const body = await this.orm.call(
                    "knowledge.article",
                    "apply_template",
                    [this.props.record.resId],
                    {
                        template_id: articleTemplateId,
                        skip_body_update: true,
                    }
                );
                this.props.editor.editable.replaceChildren(
                    parseHTML(this.props.editor.document, body)
                );
                this.props.editor.shared.selection.setCursorEnd(this.props.editor.editable);
                this.props.editor.shared.history.addStep();
                // TODO: apply_template could return all modified values on the current
                // article and record.update would reload related components
                await this.actionService.doAction(
                    "knowledge.ir_actions_server_knowledge_home_page",
                    {
                        stackPosition: "replaceCurrentAction",
                        additionalContext: {
                            res_id: this.props.record.resId,
                        },
                    }
                );
            },
        });
    }

    onBuildItemCalendarBtnClick() {
        this.dialogService.add(ItemCalendarPropsDialog, {
            isNew: true,
            knowledgeArticleId: this.props.record.resId,
            saveItemCalendarProps: async (name, itemCalendarProps) => {
                const title = name || _t("Article Items");
                const displayName = name
                    ? _t("Calendar of %s", name)
                    : _t("Calendar of Article Items");
                const embeddedProps = {
                    viewProps: {
                        additionalViewProps: { itemCalendarProps },
                        actionXmlId: "knowledge.knowledge_article_action_item_calendar",
                        displayName: displayName,
                        viewType: "calendar",
                        context: {
                            active_id: this.props.record.resId,
                            default_parent_id: this.props.record.resId,
                            default_is_article_item: true,
                        },
                    },
                };
                const fragment = renderToFragment("knowledge.ArticleItemTemplate", {
                    embeddedProps: JSON.stringify(embeddedProps),
                    title,
                });
                this.props.editor.editable.replaceChildren(...fragment.children);
                this.props.editor.shared.selection.setCursorEnd(this.props.editor.editable);
                this.props.editor.shared.history.addStep();
                this.props.record.update({ name: title });
            },
        });
    }

    onBuildItemKanbanBtnClick() {
        this.dialogService.add(PromptEmbeddedViewNameDialog, {
            isNew: true,
            viewType: "kanban",
            /**
             * @param {string} name
             */
            save: async (name) => {
                const embeddedProps = {
                    viewProps: {
                        actionXmlId: "knowledge.knowledge_article_item_action_stages",
                        displayName: name
                            ? _t("Kanban of %s", name)
                            : _t("Kanban of Article Items"),
                        viewType: "kanban",
                        context: {
                            active_id: this.props.record.resId,
                            default_parent_id: this.props.record.resId,
                            default_is_article_item: true,
                        },
                    },
                };
                const title = name || _t("Article Items");
                await this.orm.call("knowledge.article", "create_default_item_stages", [
                    this.props.record.resId,
                ]);
                const fragment = renderToFragment("knowledge.ArticleItemTemplate", {
                    embeddedProps: JSON.stringify(embeddedProps),
                    title,
                });
                this.props.editor.editable.replaceChildren(...fragment.children);
                this.props.editor.shared.selection.setCursorEnd(this.props.editor.editable);
                this.props.editor.shared.history.addStep();
                this.props.record.update({ name: title });
            },
        });
    }

    onBuildItemListBtnClick() {
        this.dialogService.add(PromptEmbeddedViewNameDialog, {
            isNew: true,
            viewType: "list",
            /**
             * @param {string} name
             */
            save: async (name) => {
                const embeddedProps = {
                    viewProps: {
                        actionXmlId: "knowledge.knowledge_article_item_action",
                        displayName: name ? _t("List of %s", name) : _t("List of Article Items"),
                        viewType: "list",
                        context: {
                            active_id: this.props.record.resId,
                            default_parent_id: this.props.record.resId,
                            default_is_article_item: true,
                        },
                    },
                };
                const title = name || _t("Article Items");

                const fragment = renderToFragment("knowledge.ArticleItemTemplate", {
                    embeddedProps: JSON.stringify(embeddedProps),
                    title,
                });
                this.props.editor.editable.replaceChildren(...fragment.children);
                this.props.editor.shared.selection.setCursorEnd(this.props.editor.editable);
                this.props.editor.shared.history.addStep();
                this.props.record.update({ name: title });
            },
        });
    }

    onGenerateArticleClick() {
        this.dialogService.add(ChatGPTPromptDialog, {
            initialPrompt: _t("Write an article about"),
            baseContainer: "P",
            insert: (fragment) => {
                const generatedContentTitle = fragment.querySelector("h1,h2");
                const articleTitle = this.props.editor.document.createElement("h1");
                if (generatedContentTitle && generatedContentTitle.tagName !== "H1") {
                    articleTitle.innerText = generatedContentTitle.innerText;
                    generatedContentTitle.replaceWith(articleTitle);
                } else if (!generatedContentTitle) {
                    const br = this.props.editor.document.createElement("BR");
                    articleTitle.replaceChildren(br);
                    fragment.prepend(articleTitle);
                }
                this.props.editor.editable.replaceChildren(...fragment.children);
                this.props.editor.shared.selection.setCursorEnd(this.props.editor.editable);
                this.props.editor.shared.history.addStep();
            },
            sanitize: (fragment) => {
                return DOMPurify.sanitize(fragment, {
                    IN_PLACE: true,
                    ADD_TAGS: ["#document-fragment"],
                    ADD_ATTR: ["contenteditable"],
                });
            },
        });
    }
}
