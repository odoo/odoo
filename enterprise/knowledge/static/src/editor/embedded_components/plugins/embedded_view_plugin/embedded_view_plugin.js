import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { ItemCalendarPropsDialog } from "@knowledge/components/item_calendar_props_dialog/item_calendar_props_dialog";
import { PromptEmbeddedViewNameDialog } from "@knowledge/components/prompt_embedded_view_name_dialog/prompt_embedded_view_name_dialog";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

function isAvailable(selection) {
    return !closestElement(selection.anchorNode, ".o_editor_banner, table, [data-embedded]");
}

export class EmbeddedViewPlugin extends Plugin {
    static id = "embeddedView";
    static dependencies = ["history", "dom", "selection"];
    resources = {
        user_commands: [
            {
                id: "insertEmbeddedViewKanban",
                title: _t("Item Kanban"),
                description: _t("Insert a Kanban view of article items"),
                icon: "fa-th-large",
                run: () => {
                    this.promptInsertEmbeddedView("kanban", true);
                },
            },
            {
                id: "insertEmbeddedViewCards",
                title: _t("Item Cards"),
                description: _t("Insert a Card view of article items"),
                icon: "fa-address-card",
                run: () => {
                    this.promptInsertEmbeddedView("kanban");
                },
            },
            {
                id: "insertEmbeddedViewList",
                title: _t("Item List"),
                description: _t("Insert a List view of article items"),
                icon: "fa-th-list",
                run: () => {
                    this.promptInsertEmbeddedView("list");
                },
            },
            {
                id: "insertEmbeddedViewCalendar",
                title: _t("Item Calendar"),
                description: _t("Insert a Calendar view of article items"),
                icon: "fa-calendar-plus-o",
                run: () => {
                    this.promptInsertEmbeddedCalendarView();
                },
            }
        ],
        powerbox_items: [
            {
                categoryId: "knowledge",
                commandId: "insertEmbeddedViewKanban",
                isAvailable,
            },
            {
                categoryId: "knowledge",
                commandId: "insertEmbeddedViewCards",
                isAvailable,
            },
            {
                categoryId: "knowledge",
                commandId: "insertEmbeddedViewList",
                isAvailable,
            },
            {
                categoryId: "knowledge",
                commandId: "insertEmbeddedViewCalendar",
                isAvailable,
            },
        ],
    };

    insertEmbeddedView(actionXmlId, name, viewType, additionalViewProps = {}) {
        const resId = this.config.getRecordInfo().resId;
        const embeddedViewBlueprint = renderToElement("knowledge.EmbeddedViewBlueprint", {
            embeddedProps: JSON.stringify({
                viewProps: {
                    actionXmlId,
                    additionalViewProps,
                    context: {
                        active_id: resId,
                        default_parent_id: resId,
                        default_is_article_item: true,
                    },
                    displayName: name,
                    viewType,
                },
            }),
        });
        this.dependencies.dom.insert(embeddedViewBlueprint);
        this.dependencies.history.addStep();
    }

    promptInsertEmbeddedCalendarView() {
        let cursor = this.dependencies.selection.preserveSelection();
        const resId = this.config.getRecordInfo().resId;
        this.services.dialog.add(
            ItemCalendarPropsDialog,
            {
                isNew: true,
                knowledgeArticleId: resId,
                saveItemCalendarProps: (name, itemCalendarProps) => {
                    cursor = null;
                    this.insertEmbeddedView(
                        "knowledge.knowledge_article_action_item_calendar",
                        name,
                        "calendar",
                        { itemCalendarProps }
                    );
                },
            },
            {
                onClose: () => {
                    cursor?.restore();
                },
            }
        );
    }

    promptInsertEmbeddedView(viewType, withStages) {
        let cursor = this.dependencies.selection.preserveSelection();
        const resId = this.config.getRecordInfo().resId;
        this.services.dialog.add(
            PromptEmbeddedViewNameDialog,
            {
                isNew: true,
                save: async (name) => {
                    cursor = null;
                    if (withStages) {
                        await this.services.orm.call(
                            "knowledge.article",
                            "create_default_item_stages",
                            [resId]
                        );
                    }
                    this.insertEmbeddedView(
                        `knowledge.knowledge_article_item_action${withStages ? "_stages" : ""}`,
                        name,
                        viewType
                    );
                },
                viewType,
            },
            {
                onClose: () => {
                    cursor?.restore();
                },
            }
        );
    }
}
