/** @odoo-module **/

import { useBus, useEffect, useService } from "@web/core/utils/hooks";
import { SearchModel } from "@web/search/search_model";
import { CallbackRecorder, useSetupAction } from "@web/webclient/actions/action_hook";

const { Component, hooks } = owl;
const { useSubEnv } = hooks;

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

        const SearchModelClass = this.Component.SearchModel || SearchModel;
        this.searchModel = new SearchModelClass(this.env, {
            user: useService("user"),
            orm: useService("orm"),
            view: useService("view"),
        });
        useBus(this.searchModel, "update", () => this.render());
        useSubEnv({
            searchModel: this.searchModel,
        });

        useSetupAction({
            exportGlobalState: () => {
                return {
                    searchModel: JSON.stringify(this.searchModel.exportState()),
                };
            },
        });

        useEffect(() => {
            if (!this.searchModel.display.searchPanel) {
                return;
            }
            // TODO: add better way to retrieve o_content
            const [content] = this.el.getElementsByClassName("o_content");
            if (content) {
                content.classList.add("o_component_with_search_panel");
            }
        });
    }

    async willStart() {
        const config = { ...this.props };
        if (config.globalState && config.globalState.searchModel) {
            config.state = JSON.parse(config.globalState.searchModel);
            delete config.globalState;
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

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get componentProps() {
        const componentProps = { ...this.props.componentProps };
        for (const key of SEARCH_KEYS) {
            componentProps[key] = this.searchModel[key];
        }
        componentProps.info = componentProps.info || {};
        for (const key of OTHER_SEARCH_KEYS) {
            componentProps.info[key] = this.searchModel[key];
        }
        return componentProps;
    }
}

WithSearch.defaultProps = {
    action: { id: false, views: [] },
    componentProps: {},
    view: { id: false },
};
WithSearch.props = {
    Component: Function,
    componentProps: { type: Object, optional: true },

    resModel: String,

    action: {
        type: Object,
        shape: {
            id: [Number, false],
            type: { type: [String, false], optional: true },
            views: { type: Array, element: [Number, String, false], optional: true },
        },
        optional: true,
    },
    displayName: { type: String, optional: true },
    view: {
        type: Object,
        shape: {
            id: [Number, false],
            type: { type: [String, false], optional: true },
        },
        optional: true,
    },

    globalState: { type: Object, optional: true },

    display: { type: Object, optional: true },

    // search query elements
    context: { type: Object, optional: true },
    domain: { type: Array, element: [String, Array], optional: true },
    domains: { type: Array, element: Object, optional: true },
    groupBy: { type: Array, element: String, optional: true },
    orderBy: { type: Array, element: String, optional: true },

    // search view description
    searchViewArch: { type: String, optional: true },
    searchViewFields: { type: Object, optional: true },
    searchViewId: { type: [Number, false], optional: true },

    irFilters: { type: Array, element: Object, optional: true },
    loadIrFilters: { type: Boolean, optional: true },

    // extra options
    activateFavorite: { type: Boolean, optional: true },
    dynamicFilters: { type: Array, element: Object, optional: true },
    searchMenuTypes: { type: Array, element: String, optional: true },
};
WithSearch.template = "web.WithSearch";
