/** @odoo-module **/

import { CallbackRecorder, useSetupAction } from "@web/webclient/actions/action_hook";
import { SearchModel } from "../search_model";
import { useService } from "@web/core/service_hook";
import { useBus } from "@web/core/bus_hook";

const { Component, hooks } = owl;
const { useSubEnv } = hooks;

const searchModelStateSymbol = Symbol("searchModelState");

export const SEARCH_KEYS = ["context", "domain", "domains", "groupBy", "orderBy"];
const OTHER_SEARCH_KEYS = ["irFilters", "searchViewArch", "searchViewFields", "searchViewId"];

export class WithSearch extends Component {
    setup() {
        this.Component = this.props.Component;

        if (!this.env.__saveParams__) {
            useSubEnv({
                __saveParams__: new CallbackRecorder(),
            });
        }

        const SearchModel = this.Component.SearchModel || this.constructor.SearchModel;
        this.searchModel = new SearchModel(this.env, {
            user: useService("user"),
            orm: useService("orm"),
            view: useService("view"),
        });
        useBus(this.searchModel, "update", () => this.render());
        useSubEnv({
            searchModel: this.searchModel,
        });

        useSetupAction({
            exportSearchState: () => {
                return {
                    [searchModelStateSymbol]: this.searchModel.exportState(),
                };
            },
        });
    }

    async willStart() {
        const config = Object.assign({}, this.props);
        if (config.searchState && config.searchState[searchModelStateSymbol]) {
            config.state = config.searchState[searchModelStateSymbol];
            delete config.searchState;
        }
        await this.searchModel.load(config);
    }

    async willUpdateProps(nextProps) {
        const config = {};
        for (const key of SEARCH_KEYS) {
            if (nextProps[key]) {
                config[key] = nextProps[key];
            }
        }
        await this.searchModel.reload(config);
    }

    get componentProps() {
        const componentProps = Object.assign({}, this.props.componentProps);
        for (const key of SEARCH_KEYS) {
            componentProps[key] = this.searchModel[key];
        }
        if (!componentProps.info) {
            componentProps.info = {};
        }
        for (const key of OTHER_SEARCH_KEYS) {
            componentProps.info[key] = this.searchModel[key];
        }
        return componentProps;
    }

    get withSearchPanel() {
        /** @todo review when working on search panel */
        return this.searchModel.loadSearchPanel;
    }
}

WithSearch.defaultProps = {
    componentProps: {},
};
WithSearch.props = {
    Component: Function,
    componentProps: { type: Object, optional: 1 },

    resModel: String,

    actionId: { type: [Number, false], optional: 1 },
    displayName: { type: String, optional: 1 },

    // search state
    searchState: { type: Object, optional: 1 },

    // search query elements
    context: { type: Object, optional: 1 },
    domain: { type: Array, element: [String, Array], optional: 1 },
    domains: { type: Array, element: Object, optional: 1 },
    groupBy: { type: Array, element: String, optional: 1 },
    orderBy: { type: Array, element: String, optional: 1 },

    // search view description
    searchViewArch: { type: String, optional: 1 },
    searchViewFields: { type: Object, optional: 1 },
    searchViewId: { type: [Number, false], optional: 1 },

    irFilters: { type: Array, element: Object, optional: 1 },
    loadIrFilters: { type: Boolean, optional: 1 },

    // extra options
    activateFavorite: { type: Boolean, optional: 1 },
    dynamicFilters: { type: Array, element: Object, optional: 1 },
    loadSearchPanel: { type: Boolean, optional: 1 },
    searchMenuTypes: { type: Array, element: String, optional: 1 },
};
WithSearch.template = "web.WithSearch";

WithSearch.SearchModel = SearchModel;
