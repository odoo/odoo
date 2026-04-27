import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { renderToElement } from "@web/core/utils/render";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

const cogMenuRegistry = registry.category("cogMenu");

const supportedEmbeddedViews = new Set([
    "calendar",
    "graph",
    "hierarchy",
    "kanban",
    "list",
    "pivot",
    "cohort",
    "gantt",
    "map",
]);

class InsertEmbeddedViewMenu extends Component {
    static props = {};
    static template = "knowledge.InsertEmbeddedViewMenu";
    static components = { Dropdown, DropdownItem };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.addDialog = useOwnedDialogs();
        this.knowledgeCommandsService = useService("knowledgeCommandsService");
    }

    /**
     * @returns {Object|null} Template props necessary to render an embedded
     *                        view in Knowledge, or null if it is not possible
     *                        to store this view as an embedded view.
     */
    extractCurrentViewEmbedTemplateProps() {
        /**
         * Note: If you change the embedded view props (i.e: context key, etc.),
         * do not forget to update the related python tests.
         */
        const viewProps = {
            context: this.getViewContext(),
            displayName: this.env.config.getDisplayName(),
            viewType: this.env.config.viewType,
        };
        const xmlId = this.actionService.currentController?.action?.xml_id;
        if (xmlId) {
            viewProps.actionXmlId = xmlId;
            return { embeddedProps: { viewProps } };
        }
        /**
         * Recover the original action (before the service pre-processing). The
         * raw action is needed because it will be pre-processed again as a
         * "different" action, after being stripped of its id, in Knowledge.
         * If there is no original action, it means that the action is not
         * serializable, therefore it cannot be stored in the body of an
         * article.
         */
        const originalAction = this.actionService.currentController?.action?._originalAction;
        if (originalAction) {
            const action = JSON.parse(originalAction);
            // remove action help as it won't be used
            delete action.help;
            viewProps.actWindow = action;
            return { embeddedProps: { viewProps } };
        }
        return null;
    }

    /**
     * Returns the full context that will be passed to the embedded view.
     * @returns {Object}
     */
    getViewContext() {
        const context = {};
        if (this.env.searchModel) {
            // Store the context of the search model:
            Object.assign(
                context,
                omit(this.env.searchModel.context, ...Object.keys(user.context))
            );
            // Store the state of the search model:
            Object.assign(context, {
                knowledge_search_model_state: JSON.stringify(this.env.searchModel.exportState()),
            });
        }
        // Store the "local context" of the view:
        const fns = this.env.__getContext__.callbacks;
        const localContext = Object.assign({}, ...fns.map((fn) => fn()));
        const extraContext = {};
        this.env.searchModel.trigger("insert-embedded-view", extraContext);
        Object.assign(context, localContext, extraContext);
        return context;
    }

    /**
     * Prepare a Embedded Component rendered in backend to be inserted in an
     * article by the KnowledgeCommandsService.
     * Allow to choose an article in a modal, redirect to that article and
     * append the rendered template "blueprint" needed for the desired Embedded
     * Component
     * @param {string} template template name of the embedded blueprint to
     *                 render.
     */
    insertCurrentViewInKnowledge(template) {
        const config = this.env.config;
        const templateProps = this.extractCurrentViewEmbedTemplateProps();
        if (config.actionType !== "ir.actions.act_window" || !templateProps) {
            throw new Error(
                'This view can not be embedded in an article: the action is not an "ir.actions.act_window" or is not serializable.'
            );
        }
        this.openArticleSelector(async (id) => {
            this.knowledgeCommandsService.setPendingEmbeddedBlueprint({
                embeddedBlueprint: renderToElement(template, {
                    embeddedProps: JSON.stringify(templateProps.embeddedProps),
                }),
                model: "knowledge.article",
                field: "body",
                resId: id,
            });
            this.actionService.doAction("knowledge.ir_actions_server_knowledge_home_page", {
                additionalContext: {
                    res_id: id,
                },
            });
        });
    }

    onInsertEmbeddedViewInArticle() {
        this.insertCurrentViewInKnowledge("knowledge.EmbeddedViewBlueprint");
    }

    onInsertViewLinkInArticle() {
        this.insertCurrentViewInKnowledge("knowledge.EmbeddedViewLinkBlueprint");
    }

    /**
     * @param {Function} onSelectCallback
     */
    openArticleSelector(onSelectCallback) {
        this.addDialog(SelectCreateDialog, {
            title: _t("Select an article"),
            noCreate: false,
            multiSelect: false,
            resModel: "knowledge.article",
            context: {},
            domain: [
                ["user_has_write_access", "=", true],
                ["is_template", "=", false],
            ],
            onSelected: (resIds) => {
                onSelectCallback(resIds[0]);
            },
            onCreateEdit: async () => {
                const articleId = await this.orm.call("knowledge.article", "article_create", [], {
                    is_private: true,
                });
                onSelectCallback(articleId);
            },
        });
    }
}

cogMenuRegistry.add("insert-embedded-view-menu", {
    Component: InsertEmbeddedViewMenu,
    groupNumber: 10,
    isDisplayed: (env) => {
        // only support act_window with an id for now, but act_window
        // object could potentially be used too (rework backend API to insert
        // views in articles)
        return (
            env.config.actionId &&
            !env.searchModel.context.knowledgeEmbeddedViewId &&
            supportedEmbeddedViews.has(env.config.viewType)
        );
    },
});
