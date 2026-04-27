import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { EmbeddedView } from "@knowledge/views/embedded_view";
import { WithLazyLoading } from "@knowledge/components/with_lazy_loading/with_lazy_loading";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { useBus, useService } from "@web/core/utils/hooks";
import { CallbackRecorder } from "@web/search/action_hook";
import { getDefaultConfig } from "@web/views/view";

import {
    Component,
    onError,
    onWillStart,
    useExternalListener,
    useState,
    useSubEnv,
} from "@odoo/owl";

const VIEW_RECORDS_LIMITS = {
    kanban: 20,
    list: 40,
};

export class ReadonlyEmbeddedViewComponent extends Component {
    static components = {
        EmbeddedView,
        WithLazyLoading
    };
    static props = {
        host: { type: Object },
        viewProps: { type: Object },
    };
    static template = "knowledge.EmbeddedView";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.uiService = useService("ui");
        this.viewFilters = useService("knowledgeEmbedViewsFilters");
        useOwnDebugContext(); // define a debug context when the developer mode is enable
        this.state = useState({
            error: false,
            isLoaded: false,
        });
        const services = this.env.services;
        const extendedServices = Object.create(services);
        extendedServices.action = Object.create(services.action);
        extendedServices.action.switchView = (viewType, props = {}) => {
            if (props.resId) {
                this.action.res_id = props.resId;
            }
            this.action.globalState = this.getEmbeddedViewGlobalState();
            this.actionService.doAction(this.action, { viewType });
        };

        useSubEnv({
            config: { ...getDefaultConfig(), disableSearchBarAutofocus: true },
            isEmbeddedView: true,
            isEmbeddedReadonly: true,
            services: extendedServices,
        });

        useBus(this.env.bus, `KNOWLEDGE_EMBEDDED_${this.id}:OPEN`, () => {
            this.openView();
        });

        /**
         * Normally, the editable is the only element in the editor which has the focus.
         * In this case, it can be useful to delegate the focus at a lower level
         * (i.e. to use hotkeys with the uiService).
         *
         * `activateElement` is used to set the host as an active element in the ui service, this enables
         * us to contain the events inside the embedded view when it has the focus.
         *
         * `deactivateElement` removes the host as an active element, leaving only the document as active
         * and we come back to the default behavior of the document handling all the events.
         *
         * As a reminder, tabindex="-1" must be set in the template for an element to capture
         * focusin and focusout events.
         */
        useExternalListener(this.props.host, "focusin", () => {
            if (!this.props.host.contains(this.uiService.activeElement)) {
                this.uiService.activateElement(this.props.host);
            }
        });
        useExternalListener(this.props.host, "focusout", (event) => {
            if (!this.props.host.contains(event.relatedTarget)) {
                this.uiService.deactivateElement(this.props.host);
            }
        });

        onWillStart(async () => {
            await this.loadEmbeddedView();
        });

        // TODO ABD: better error handling (discard filters)
        onError((error) => {
            console.error(error);
            this.state.error = true;
        });
    }

    get embeddedViewProps() {
        // forces reactivity for additionalViewProps, displayName and
        // favoriteFilters
        return {
            ...this.staticEmbeddedViewProps,
            additionalViewProps: { ...this.additionalViewProps },
            displayName: this.displayName,
            irFilters: this.irFilters,
        };
    }

    get additionalViewProps() {
        return this.props.viewProps.additionalViewProps;
    }

    get displayName() {
        return this.props.viewProps.displayName;
    }

    get favoriteFilters() {
        return this.props.viewProps.favoriteFilters;
    }

    get id() {
        return this.props.viewProps.id;
    }

    get irFilters() {
        // TODO ABD: make collaborative filters update reactive since the embedded state is updated,
        // it should be possible to update the searchModel too.
        return (Object.values(this.favoriteFilters || {}) || []).map((filter) => ({
            ...filter,
            context: JSON.stringify(filter.context),
        }));
    }

    async createRecord() {
        this.saveFilters();
        // can we use res_id: false and thus make one method for select and create?
        this.actionService.doAction({
            res_model: this.action.res_model,
            type: 'ir.actions.act_window',
            views: [this.action.views.find(([_, type]) => type === "form") || [false, "form"]],
        });
    }

    deleteFavoriteFilter(searchItem) {
        this.notificationService.add(
            _t("You are not allowed to delete a favorite filter in this article."),
            {
                type: "danger",
            }
        );
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

    async loadEmbeddedView() {
        // allow access to the SearchModel exported state which contain facets
        this.__getGlobalState__ = new CallbackRecorder();
        const context = this.makeEmbeddedContext();
        this.action = await this.loadAction(context);
        this.env.config.views = this.action.views;
        this.env.config.setDisplayName(this.action.name);
        this.staticEmbeddedViewProps = this.prepareStaticEmbeddedViewProps(context);
        this.viewFilters.applyFilter(
            this.actionService.currentController,
            this.id,
            this.staticEmbeddedViewProps
        );
        this.state.isLoaded = true;
    }

    async loadAction(context) {
        // never use an action help with actWindow (could have been added by a malicious user)
        if (this.props.actWindow?.help) {
            delete this.props.actWindow.help;
        }
        const action = await this.actionService.loadAction(
            this.props.viewProps.actWindow || this.props.viewProps.actionXmlId,
            context
        );
        if (action.type !== "ir.actions.act_window") {
            throw new Error(
                `Invalid action type "${action.type}". Expected "ir.actions.act_window"`
            );
        }
        if (this.displayName) {
            action.name = this.displayName;
            action.display_name = this.displayName;
        }
        return action;
    }

    /**
     * Create the context used by the embedded view.
     */
    makeEmbeddedContext() {
        const context = makeContext([
            this.props.viewProps.context || {},
            {
                knowledgeEmbeddedViewId: this.id,
            },
        ]);
        return context;
    }

    /**
     * Open the view in "full screen"
     */
    openView() {
        this.saveFilters();
        const props = { ...(this.additionalViewProps || {}) };
        if (this.action.context.orderBy) {
            try {
                props.orderBy = JSON.parse(this.action.context.orderBy);
            } catch {
                console.error("Parsing orderBy failed");
            }
        }
        // make sure name is up to date (could have been updated by collaborative)
        if (this.displayName !== this.action.display_name) {
            this.action.display_name = this.displayName;
            this.action.name = this.displayName;
        }
        this.action.globalState = this.getEmbeddedViewGlobalState();
        this.actionService.doAction(this.action, {
            viewType: this.props.viewProps.viewType,
            props,
            additionalContext: {
                knowledgeEmbeddedViewId: this.id,
                isOpenedEmbeddedView: true,
            },
        });
    }

    prepareStaticEmbeddedViewProps(context) {
        return {
            context,
            createRecord: this.createRecord.bind(this),
            deleteEmbeddedViewFavoriteFilter: this.deleteFavoriteFilter.bind(this),
            domain: this.action.domain || [],
            __getGlobalState__: this.__getGlobalState__,
            globalState: { searchModel: context.knowledge_search_model_state },
            irFilters: this.irFilters,
            limit: VIEW_RECORDS_LIMITS[this.props.viewProps.type],
            loadActionMenus: true,
            loadIrFilters: true,
            noContentHelp: this.action.help,
            resModel: this.action.res_model,
            saveEmbeddedViewFavoriteFilter: this.saveFavoriteFilter.bind(this),
            searchViewId: this.action.searchViewId?.[0],
            selectRecord: this.selectRecord.bind(this),
            type: this.props.viewProps.viewType,
        };
    }

    saveFilters() {
        this.viewFilters.saveFilters(
            this.actionService.currentController,
            this.id,
            this.getEmbeddedViewGlobalState().searchModel
        );
    }

    saveFavoriteFilter(filter) {
        this.notificationService.add(
            _t("You are not allowed to save a favorite filter in this article."),
            {
                type: "danger",
            }
        );
    }

    selectRecord(resId) {
        this.saveFilters();
        if (this.action.res_model === "knowledge.article") {
            this.env.openArticle(resId);
        } else {
            this.actionService.doAction({
                res_id: resId,
                res_model: this.action.res_model,
                type: "ir.actions.act_window",
                views: [this.action.views.find((_, type) => type === "form") || [false, "form"]],
            });
        }
    }
}

export const readonlyViewEmbedding = {
    name: "view",
    Component: ReadonlyEmbeddedViewComponent,
    getProps: (host) => {
        return { host, ...getEmbeddedProps(host) };
    },
};
