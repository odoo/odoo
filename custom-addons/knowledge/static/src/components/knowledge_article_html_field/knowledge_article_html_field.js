/** @odoo-module */

import { renderToString } from "@web/core/utils/render";
import { ArticleTemplatePickerDialog } from "@knowledge/components/article_template_picker_dialog/article_template_picker_dialog";
import { encodeDataBehaviorProps } from "@knowledge/js/knowledge_utils";
import { HtmlField, htmlField } from "@web_editor/js/backend/html_field";
import { ItemCalendarPropsDialog } from "@knowledge/components/item_calendar_props_dialog/item_calendar_props_dialog";
import {
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
} from "@odoo/owl";
import { KnowledgePlugin } from "@knowledge/js/knowledge_plugin";
import { PromptEmbeddedViewNameDialog } from "@knowledge/components/prompt_embedded_view_name_dialog/prompt_embedded_view_name_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";


/**
 * This component will extend the HTML field of Knowledge and show an helper
 * when the article is empty. The helper will suggest the user to:
 * - Load a Template
 * - Build an Item Kanban
 * - Build an Item List
 * - Build an Item Calendar
 */
export class KnowledgeArticleHtmlField extends HtmlField {
    static template = "knowledge.KnowledgeArticleHtmlField";

    /**
     * @override
     */
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.userService = useService('user');
        onWillUpdateProps(nextProps => {
            this.state.isWysiwygHelperActive = this.isWysiwygHelperActive(nextProps);
        });
        this.editorStepsCallback = () => this.state.isEmpty = this.wysiwyg.isEmpty();
        onWillUnmount(() => {
            if (this.wysiwyg?.odooEditor) {
                this.wysiwyg.odooEditor.removeEventListener("historyStep", this.editorStepsCallback);
                this.wysiwyg.odooEditor.removeEventListener("onExternalHistorySteps", this.editorStepsCallback);
                this.wysiwyg.odooEditor.removeEventListener("historyResetFromSteps", this.editorStepsCallback);
            }
        });
        onWillStart(async () => {
            this.isPortalUser = await this.userService.hasGroup('base.group_portal');
        })
    }

    get wysiwygOptions() {
        const wysiwygOptions = super.wysiwygOptions;
        wysiwygOptions.editorPlugins = [...wysiwygOptions.editorPlugins, KnowledgePlugin];
        return wysiwygOptions;
    }

    /**
     * @override
     * @param {Widget} wysiwyg
     */
    async startWysiwyg(wysiwyg) {
        await super.startWysiwyg(wysiwyg);
        Object.assign(this.state, {
            isEmpty: this.wysiwyg.isEmpty(),
            isWysiwygHelperActive: this.isWysiwygHelperActive(this.props)
        });
        this.wysiwyg.odooEditor.addEventListener("historyStep", this.editorStepsCallback);
        this.wysiwyg.odooEditor.addEventListener("onExternalHistorySteps", this.editorStepsCallback);
        this.wysiwyg.odooEditor.addEventListener("historyResetFromSteps", this.editorStepsCallback);
    }

    /**
     * @param {Object} props
     * @returns {boolean}
     */
    isWysiwygHelperActive(props) {
        return !props.readonly && !props.record.data.is_article_item;
    }

    onLoadTemplateBtnClick() {
        this.dialogService.add(ArticleTemplatePickerDialog, {
            onLoadTemplate: async articleTemplateId => {
                const body = await this.orm.call("knowledge.article", "apply_template", [this.props.record.resId], {
                    template_id: articleTemplateId,
                    skip_body_update: true
                });
                this.wysiwyg.setValue(body);
                await this.actionService.doAction("knowledge.ir_actions_server_knowledge_home_page", {
                    stackPosition: "replaceCurrentAction",
                    additionalContext: {
                        res_id: this.props.record.resId
                    }
                });
            }
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
                const behaviorProps = {
                    action_xml_id: "knowledge.knowledge_article_action_item_calendar",
                    display_name: displayName,
                    view_type: "calendar",
                    context: {
                        active_id: this.props.record.resId,
                        default_parent_id: this.props.record.resId,
                        default_is_article_item: true,
                    },
                    additionalViewProps: { itemCalendarProps },
                };
                const body = renderToString("knowledge.article_item_template", {
                    behaviorProps: encodeDataBehaviorProps(behaviorProps),
                    title,
                });
                this.updateArticle(title, body, {
                    full_width: true,
                });
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
            save: async name => {
                const behaviorProps = {
                    action_xml_id: "knowledge.knowledge_article_item_action_stages",
                    display_name: name ? _t("Kanban of %s", name) : _t("Kanban of Article Items"),
                    view_type: "kanban",
                    context: {
                        active_id: this.props.record.resId,
                        default_parent_id: this.props.record.resId,
                        default_is_article_item: true,
                    }
                };
                const title = name || _t("Article Items");
                const body = renderToString("knowledge.article_item_template", {
                    behaviorProps: encodeDataBehaviorProps(behaviorProps),
                    title
                });
                await this.orm.call("knowledge.article", "create_default_item_stages", [this.props.record.resId]);
                this.updateArticle(title, body, {
                    full_width: true
                });
            }
        });
    }

    onBuildItemListBtnClick() {
        this.dialogService.add(PromptEmbeddedViewNameDialog, {
            isNew: true,
            viewType: "list",
            /**
             * @param {string} name
             */
            save: async name => {
                const behaviorProps = {
                    action_xml_id: "knowledge.knowledge_article_item_action",
                    display_name: name ? _t("List of %s", name) : _t("List of Article Items"),
                    view_type: "list",
                    context: {
                        active_id: this.props.record.resId,
                        default_parent_id: this.props.record.resId,
                        default_is_article_item: true,
                    }
                };
                const title = name || _t("Article Items");
                const body = renderToString("knowledge.article_item_template", {
                    behaviorProps: encodeDataBehaviorProps(behaviorProps),
                    title
                });
                this.updateArticle(title, body, {
                    full_width: true
                });
            }
        });
    }

    onGenerateArticleClick() {
        this.wysiwyg.generateArticle();
    }

    /**
     * @param {string} title
     * @param {string} body
     * @param {Object} values
     */
    async updateArticle(title, body, values) {
        this.wysiwyg.setValue(body);
        await this.props.record.update({
            ...values,
            name: title,
        });
    }

    async _lazyloadWysiwyg() {
        await super._lazyloadWysiwyg(...arguments);
        this.Wysiwyg = (await odoo.loader.modules.get('@knowledge/js/knowledge_wysiwyg')).KnowledgeWysiwyg;
    }
}

export const knowledgeArticleHtmlField = Object.assign(Object.create(htmlField), {
    component: KnowledgeArticleHtmlField,
});

registry.category("fields").add("knowledge_article_html_field", knowledgeArticleHtmlField);
