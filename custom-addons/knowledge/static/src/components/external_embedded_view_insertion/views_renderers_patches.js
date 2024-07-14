/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { memoize } from "@web/core/utils/functions";
import { renderToElement } from "@web/core/utils/render";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { MapRenderer } from "@web_map/map_view/map_renderer";
import { patch } from "@web/core/utils/patch";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import {
    useBus,
    useOwnedDialogs,
    useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { encodeDataBehaviorProps } from "@knowledge/js/knowledge_utils";

/**
 * The following patch will add two new entries to the 'Favorites' dropdown menu
 * of the control panel namely: 'Insert view in article' and 'Insert link in article'.
 */
const EmbeddedViewRendererPatch = () => ({
    setup() {
        super.setup(...arguments);
        if (this.env.searchModel) {
            useBus(this.env.searchModel, 'insert-embedded-view', this._insertCurrentViewInKnowledge.bind(this, 'knowledge.EmbeddedViewBehaviorBlueprint'));
            useBus(this.env.searchModel, 'insert-view-link', this._insertCurrentViewInKnowledge.bind(this, 'knowledge.EmbeddedViewLinkBehaviorBlueprint'));
            this.orm = useService('orm');
            this.actionService = useService('action');
            this.addDialog = useOwnedDialogs();
            this.userService = useService('user');
            this.knowledgeCommandsService = useService('knowledgeCommandsService');
        }
    },
    /**
     * @param {string} isView TODO remove with upgrade, future improvements
     *                 will use 'display_name' everywhere, currently we have to
     *                 fetch the right name prop depending on embed type.
     *                 view_link_behavior uses "name" and embedded_view_behavior
     *                 uses "display_name".
     * @returns {Object|null} Template props necessary to render an embedded
     *                        view in Knowledge, or null if it is not possible
     *                        to store this view as an embedded view.
     */
    _extractCurrentViewEmbedTemplateProps(isView=true) {
        const config = this.env.config;
        const xmlId = this.actionService.currentController?.action?.xml_id;
        const context = this._getViewContext();
        const display_name = config.getDisplayName();
        const nameProp = isView ? {
            // used by embedded view behavior
            display_name: display_name,
        } : {
            // used by view link behavior TODO: remove with upgrade
            name: display_name,
        };
        if (xmlId) {
            return {
                behaviorProps: encodeDataBehaviorProps({
                    action_xml_id: xmlId,
                    context,
                    view_type: config.viewType,
                    ...nameProp,
                }),
            };
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
            // Don't keep the non-markup help (to not store it in
            // `data-behavior-props`)
            delete action.help;
            // Recover the markup version of the act_window help field.
            const help = this.actionService.currentController.action.help;
            action.display_name = display_name;
            return {
                behaviorProps: encodeDataBehaviorProps({
                    act_window: action,
                    context,
                    view_type: config.viewType,
                    ...nameProp,
                }),
                action_help: help,
            };
        }
        return null;
    },
    /**
     * Returns the full context that will be passed to the embedded view.
     * @returns {Object}
     */
    _getViewContext() {
        const context = {};
        if (this.env.searchModel) {
            // Store the context of the search model:
            Object.assign(context, omit(this.env.searchModel.context, ...Object.keys(this.userService.context)));
            // Store the state of the search model:
            Object.assign(context, {
                knowledge_search_model_state: JSON.stringify(this.env.searchModel.exportState())
            });
        }
        // Store the "local context" of the view:
        const fns = this.env.__getContext__.callbacks;
        const localContext = Object.assign({}, ...fns.map(fn => fn()));
        Object.assign(context, localContext);
        return context;
    },
    /**
     * Prepare a Behavior rendered in backend to be inserted in an article by
     * the KnowledgeCommandsService.
     * Allow to choose an article in a modal, redirect to that article and
     * append the rendered template "blueprint" needed for the desired Behavior
     *
     * @param {string} template template name of the Behavior's blueprint to
     *                 render.
     */
    _insertCurrentViewInKnowledge(template) {
        const config = this.env.config;
        const templateProps = this._extractCurrentViewEmbedTemplateProps(template === "knowledge.EmbeddedViewBehaviorBlueprint");
        if (config.actionType !== 'ir.actions.act_window' || !templateProps) {
            throw new Error('This view can not be embedded in an article: the action is not an "ir.actions.act_window" or is not serializable.');
        }
        this._openArticleSelector(async id => {
            this.knowledgeCommandsService.setPendingBehaviorBlueprint({
                behaviorBlueprint: renderToElement(
                    template,
                    templateProps,
                ),
                model: 'knowledge.article',
                field: 'body',
                resId: id,
            });
            this.actionService.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                additionalContext: {
                    res_id: id
                }
            });
        });
    },
    /**
     * @param {Function} onSelectCallback
     */
    _openArticleSelector(onSelectCallback) {
        this.addDialog(SelectCreateDialog, {
            title: _t('Select an article'),
            noCreate: false,
            multiSelect: false,
            resModel: 'knowledge.article',
            context: {},
            domain: [
                ['user_has_write_access', '=', true],
                ['is_template', '=', false]
            ],
            onSelected: resIds => {
                onSelectCallback(resIds[0]);
            },
            onCreateEdit: async () => {
                const articleId = await this.orm.call('knowledge.article', 'article_create', [], {
                    is_private: true
                });
                onSelectCallback(articleId);
            },
        });
    },
});

const EmbeddedViewListRendererPatch = () => ({
    /**
     * @override
     * @returns {Object}
     */
    _getViewContext() {
        const context = super._getViewContext();
        Object.assign(context, {
            orderBy: JSON.stringify(this.props.list.orderBy),
            keyOptionalFields: this.keyOptionalFields,
        });
        return context;
    },
    /**
     * When the user hides/shows some columns from the list view, the system will
     * add a new cache entry in the local storage of the user and will list all
     * visible columns for the current view. To make the configuration specific to
     * a view, the system generates a unique key for the cache entry by using all
     * available information about the view.
     *
     * When loading the view, the system regenerates a key from the current view
     * and check if there is any entry in the cache for that key. If there is a
     * match, the system will load the configuration specified in the cache entry.
     *
     * For the embedded views of Knowledge, we want the configuration of the view
     * to be unique for each embedded view. To achieve that, we will overwrite the
     * function generating the key for the cache entry and include the unique id
     * of the embedded view.
     *
     * @override
     * @returns {string}
     */
    createKeyOptionalFields () {
        const embeddedViewId = this.env.searchModel ? this.env.searchModel.context.knowledgeEmbeddedViewId : null;
        if (this.env.searchModel && this.env.searchModel.context.keyOptionalFields) {
            const searchModelKeyOptionalFields = this.env.searchModel.context.keyOptionalFields;
            return searchModelKeyOptionalFields.includes(embeddedViewId)
                ? searchModelKeyOptionalFields
                : searchModelKeyOptionalFields + (embeddedViewId ? `,${embeddedViewId}` : "");
        }
        return super.createKeyOptionalFields(...arguments) + (embeddedViewId ? "," + embeddedViewId : "");
    },
});

patch(CalendarRenderer.prototype, EmbeddedViewRendererPatch());
patch(GraphRenderer.prototype, EmbeddedViewRendererPatch());
patch(HierarchyRenderer.prototype, EmbeddedViewRendererPatch());
patch(KanbanRenderer.prototype, EmbeddedViewRendererPatch());
patch(ListRenderer.prototype, EmbeddedViewRendererPatch());
patch(ListRenderer.prototype, EmbeddedViewListRendererPatch());
patch(MapRenderer.prototype, EmbeddedViewRendererPatch());
patch(PivotRenderer.prototype, EmbeddedViewRendererPatch());

const supportedEmbeddedViews = new Set([
    'calendar',
    'graph',
    'hierarchy',
    'kanban',
    'list',
    'map',
    'pivot',
]);

const externalModules = {
    "@web_cohort/cohort_renderer": {
        renderer: "CohortRenderer",
        view: "cohort",
    },
    "@web_gantt/gantt_renderer": {
        renderer: "GanttRenderer",
        view: "gantt",
    },
};

/**
 * Ensure that a patch is only applied once for each module.
 */
const patchExternalModule = memoize((path) => {
    const { [externalModules[path].renderer]: Renderer } = odoo.loader.modules.get(path) || {};
    if (Renderer) {
        patch(Renderer.prototype, EmbeddedViewRendererPatch());
        supportedEmbeddedViews.add(externalModules[path].view);
    }
});

/**
 * Apply all patches.
 */
const patchExternalModules = () => {
    for (const path of Object.keys(externalModules)) {
        patchExternalModule(path);
    }
};

// Apply a patch to a lazy-loaded module.
odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.detail.moduleName in externalModules) {
        patchExternalModule(e.detail.moduleName);
    }
});

if (odoo.loader.checkErrorProm) {
    // Apply all patches after every non-lazy module finished loading.
    odoo.loader.checkErrorProm.then(patchExternalModules);
} else {
    // Apply all patches in case the current file is a lazy-loaded module.
    patchExternalModules();
}

export {
    supportedEmbeddedViews,
};
