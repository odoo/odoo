/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CallbackRecorder } from "@web/webclient/actions/action_hook";
import { getDefaultConfig } from "@web/views/view";
import { EmbeddedView } from "@knowledge/views/embedded_view";
import { ItemCalendarPropsDialog } from "@knowledge/components/item_calendar_props_dialog/item_calendar_props_dialog";
import { PromptEmbeddedViewNameDialog } from "@knowledge/components/prompt_embedded_view_name_dialog/prompt_embedded_view_name_dialog";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { useBus, useService } from "@web/core/utils/hooks";
import {
    Component,
    onWillStart,
    useState,
    useSubEnv
} from "@odoo/owl";
import { decodeDataBehaviorProps, encodeDataBehaviorProps } from "@knowledge/js/knowledge_utils";


const EMBEDDED_VIEW_LIMITS = {
    kanban: 20,
    list: 40,
};

/**
 * Wrapper for the embedded view, manage the toolbar and the embedded view props
 */
export class EmbeddedViewManager extends Component {
    static props = {
        action: { type: Object },
        additionalViewProps: { type: Object, optional: true },
        anchor: { type: HTMLElement },
        context: { type: Object },
        getTitle: { type: Function },
        setTitle: { type: Function },
        readonly: { type: Boolean },
        record: { type: Object },
        viewType: { type: String },
    };
    static template = 'knowledge.EmbeddedViewManager';

    setup() {
        // allow access to the SearchModel exported state which contain facets
        this.__getGlobalState__ = new CallbackRecorder();

        this.actionService = useService('action');
        this.dialogService = useService('dialog');
        this.notification = useService("notification");
        this.embedViewsFilterService = useService('knowledgeEmbedViewsFilters');

        useOwnDebugContext(); // define a debug context when the developer mode is enable
        const config = {
            ...getDefaultConfig(),
            disableSearchBarAutofocus: true,
        };

        // In addition to the base viewProps (view type, model, domain, ...),
        // embedded views can have additionalViewProps that can be edited by
        // the end user, that are stored in the behaviorProps and that are used
        // to load the view.
        // These are for example currently used by the item calendar view to
        // store the start and end date properties that the model should use.
        this.state = useState({additionalViewProps: this.props.additionalViewProps});

        useBus(this.env.bus, `KNOWLEDGE_EMBEDDED_${this.props.context.knowledgeEmbeddedViewId}:EDIT`, () => {
            if (this.props.additionalViewProps) {
                this._onEditBtnClick(this);
            } else {
                this._onRenameBtnClick(this);
            }
        });
        useBus(this.env.bus, `KNOWLEDGE_EMBEDDED_${this.props.context.knowledgeEmbeddedViewId}:OPEN`, () => {
            this._onOpenBtnClick(this);
        });
        /**
         * @param {ViewType} viewType
         * @param {Object} [props={}]
         */
        const switchView = (viewType, props = {}) => {
            if (this.action.type !== "ir.actions.act_window") {
                throw new Error('Can not open the view: The action is not an "ir.actions.act_window"');
            }
            if (props.resId) {
                this.action.res_id = props.resId;
            }
            this.action.globalState = this.getEmbeddedViewGlobalState();
            this.actionService.doAction(this.action, {
                viewType: viewType,
            });
        };

        const services = this.env.services;
        const extendedServices = Object.create(services);
        extendedServices.action = Object.create(services.action);
        extendedServices.action.switchView = switchView;

        useSubEnv({
            config,
            isEmbeddedView: true,
            services: extendedServices,
        });
        onWillStart(this.onWillStart.bind(this));
    }

    /**
     * Edit the props used to render the item calendar
     */
    editItemCalendarProps() {
        this.dialogService.add(ItemCalendarPropsDialog, {
            isNew: false,
            name: this.props.getTitle(),
            saveItemCalendarProps: async (name, itemCalendarProps) => {
                this.props.setTitle(name);
                this.state.additionalViewProps.itemCalendarProps = itemCalendarProps;
                const behaviorProps = decodeDataBehaviorProps(this.props.anchor.dataset.behaviorProps);
                behaviorProps.additionalViewProps.itemCalendarProps = itemCalendarProps;
                this.props.anchor.dataset.behaviorProps = encodeDataBehaviorProps(behaviorProps);
            },
            knowledgeArticleId: this.embeddedViewProps.context.active_id,
            ...this.state.additionalViewProps.itemCalendarProps,
        });
    }

    get allEmbeddedViewProps() {
        return {...this.embeddedViewProps, additionalViewProps: {...this.state.additionalViewProps}};
    }

    /**
     * Extract the SearchModel state of the embedded view
     *
     * @returns {Object} globalState
     */
    getEmbeddedViewGlobalState() {
        const callbacks = this.__getGlobalState__.callbacks;
        let globalState;
        if (callbacks.length) {
            globalState = callbacks.reduce((res, callback) => {
                return { ...res, ...callback() };
            }, {});
        }
        return { searchModel: globalState && globalState.searchModel };
    }

    /**
     * Save the search favorite in the view arch.
     */
    async onSaveKnowledgeFavorite(favorite) {
        if (this.props.readonly) {
            this.notification.add(_t("You can not save favorite on this article"), {
                type: "danger",
            });
            return;
        }
        const data = decodeDataBehaviorProps(this.props.anchor.getAttribute("data-behavior-props"));
        const favorites = data.favorites || [];
        favorites.push(favorite);
        data.favorites = favorites;
        this.props.anchor.setAttribute("data-behavior-props", encodeDataBehaviorProps(data));
    }

    /**
     * Delete the search favorite from the view arch.
     */
    async onDeleteKnowledgeFavorite(searchItem) {
        if (this.props.readonly) {
            this.notification.add(_t("You can not delete favorite from this article"), {
                type: "danger",
            });
            return;
        }

        const data = decodeDataBehaviorProps(this.props.anchor.getAttribute("data-behavior-props"));
        const favorites = data.favorites || [];
        data.favorites = favorites.filter((favorite) => favorite.name != searchItem.description);
        this.props.anchor.setAttribute("data-behavior-props", encodeDataBehaviorProps(data));
    }

    /**
     * Recover the action from its parsed state (attrs of the Behavior block)
     * and setup the embedded view props
     */
    onWillStart () {
        const { action, context, viewType } = this.props;
        const contextKeyOptionalFields = context.keyOptionalFields;
        if (contextKeyOptionalFields && !contextKeyOptionalFields.includes(context.knowledgeEmbeddedViewId)) {
            // If the key from the context does not contain the embeddedViewId this means that we are inserting
            // a brand new embed. Thus we are adding the optionalFields stored with contextKeyOptionalFields
            // inside the localStorage with a key that contains the embeddedViewId.
            // This way when we are rendering the embedded view and its fullscreen version we are using the correct
            // key and rendering the correct fields.
            const optionalFields = localStorage.getItem(contextKeyOptionalFields);
            if (optionalFields !== null && !localStorage.getItem(contextKeyOptionalFields+`,${context.knowledgeEmbeddedViewId}`)) {
                localStorage.setItem(contextKeyOptionalFields+`,${context.knowledgeEmbeddedViewId}`, optionalFields);
                context.keyOptionalFields = contextKeyOptionalFields+`,${context.knowledgeEmbeddedViewId}`;
            }
        }
        this.env.config.setDisplayName(action.display_name);
        this.env.config.views = action.views;
        const viewProps = {
            resModel: action.res_model,
            context: context,
            domain: action.domain || [],
            type: viewType,
            loadIrFilters: true,
            loadActionMenus: true,
            __getGlobalState__: this.__getGlobalState__,
            globalState: { searchModel: context.knowledge_search_model_state },
            /**
             * @param {integer} recordId
             */
            selectRecord: recordId => {
                const [formViewId] = this.action.views.find((view) => {
                    return view[1] === 'form';
                }) || [false];
                this.saveEmbedViewFilters();
                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    res_model: action.res_model,
                    views: [[formViewId, 'form']],
                    res_id: recordId,
                });
            },
            createRecord: async () => {
                const [formViewId] = this.action.views.find((view) => {
                    return view[1] === 'form';
                }) || [false];
                this.saveEmbedViewFilters();
                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    res_model: action.res_model,
                    views: [[formViewId, 'form']],
                });
            },
        };
        if (action.search_view_id) {
            viewProps.searchViewId = action.search_view_id[0];
        }
        if (context.orderBy) {
            try {
                viewProps.orderBy = JSON.parse(context.orderBy);
            } catch {};
        }
        if (this.props.viewType in EMBEDDED_VIEW_LIMITS) {
            viewProps.limit = EMBEDDED_VIEW_LIMITS[this.props.viewType];
        }
        viewProps.irFilters = this._loadKnowledgeFavorites();
        viewProps.onSaveKnowledgeFavorite = this.onSaveKnowledgeFavorite.bind(this);
        viewProps.onDeleteKnowledgeFavorite = this.onDeleteKnowledgeFavorite.bind(this);

        this.EmbeddedView = EmbeddedView;
        this.embedViewsFilterService.applyFilter(
            this.actionService.currentController,
            this.props.context.knowledgeEmbeddedViewId,
            viewProps
        );
        this.embeddedViewProps = viewProps;
        this.action = action;
    }

    /**
     * Edit an embedded view.
     * Each embedded view that needs "additionalProps" should implement their
     * own edition dialog.
     */
    _onEditBtnClick() {
        if (this.embeddedViewProps.resModel === "knowledge.article" && this.embeddedViewProps.type === "calendar") {
            this.editItemCalendarProps();
        } else {
            throw new Error("Can not edit the view: The dialog is not implemented");
        }
    }

    /**
     * Rename an embedded view
     */
    _onRenameBtnClick () {
        this.dialogService.add(PromptEmbeddedViewNameDialog, {
            isNew: false,
            defaultName: this.props.getTitle(),
            viewType: this.props.viewType,
            save: name => {
                this.props.setTitle(name);
            },
            close: () => {}
        });
    }

    /**
     * Open an embedded view (fullscreen)
     */
    _onOpenBtnClick () {
        if (this.action.type !== "ir.actions.act_window") {
            throw new Error('Can not open the view: The action is not an "ir.actions.act_window"');
        }
        const props = this.state.additionalViewProps || {};
        if (this.action.context.orderBy) {
            try {
                props.orderBy = JSON.parse(this.action.context.orderBy);
            } catch {};
        }
        this.saveEmbedViewFilters();
        this.action.globalState = this.getEmbeddedViewGlobalState();
        this.actionService.doAction(this.action, {
            viewType: this.props.viewType,
            props,
            additionalContext: {
                knowledgeEmbeddedViewId: this.props.context.knowledgeEmbeddedViewId,
                isOpenedEmbeddedView: true
            }
        });
    }

    /**
     * This function is called when opening a record from an embedded list or kanban view or when creating
     * a new record in the said view.
     * This function calls the correct function of the filter service in order to save the searchModel of the
     * view.
     * By saving the searchModel we allow filters applied to a view to be reassigned to it when coming back
     * via the breadcrumbs created by opening/creating a record.
     */
    saveEmbedViewFilters() {
        this.embedViewsFilterService.saveFilters(
            this.actionService.currentController,
            this.props.context.knowledgeEmbeddedViewId,
            this.getEmbeddedViewGlobalState().searchModel
        );
    }

    /**
     * Load search favorites from the view arch.
     */
    _loadKnowledgeFavorites() {
        const data = decodeDataBehaviorProps(this.props.anchor.getAttribute("data-behavior-props"));
        const favorites = data.favorites || [];

        return favorites.map((favorite) => {
            favorite.isActive = favorite.isActive || false;
            favorite.context = JSON.stringify(favorite.context);
            return favorite;
        });
    }
}
