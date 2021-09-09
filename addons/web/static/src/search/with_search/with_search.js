/** @odoo-module **/

import { useBus, useService } from "@web/core/utils/hooks";
import { SearchModel } from "@web/search/search_model";
import { CallbackRecorder, useSetupAction } from "@web/webclient/actions/action_hook";

const { Component, hooks } = owl;
const { useSubEnv } = hooks;

export const SEARCH_KEYS = ["comparison", "context", "domain", "groupBy", "orderBy"];
const OTHER_SEARCH_KEYS = ["irFilters", "searchViewArch", "searchViewFields", "searchViewId"];

export class WithSearch extends Component {
    setup() {
        this.Component = this.props.Component;

        if (!this.env.__getContext__) {
            useSubEnv({ __getContext__: new CallbackRecorder() });
        }

        const SearchModelClass = this.Component.SearchModel || SearchModel;
        this.env.searchModel = new SearchModelClass(this.env, {
            user: useService("user"),
            orm: useService("orm"),
            view: useService("view"),
        });

        useBus(this.env.searchModel, "update", this.render);
        useSetupAction({
            getGlobalState: () => {
                return {
                    searchModel: JSON.stringify(this.env.searchModel.exportState()),
                };
            },
        });
    }

    async willStart() {
        const config = { ...this.props };
        if (config.globalState && config.globalState.searchModel) {
            config.state = JSON.parse(config.globalState.searchModel);
            delete config.globalState;
        }
        await this.env.searchModel.load(config);
    }

    async willUpdateProps(nextProps) {
        const config = {};
        for (const key of SEARCH_KEYS) {
            if (nextProps[key] !== undefined) {
                config[key] = nextProps[key];
            }
        }
        await this.env.searchModel.reload(config);
    }

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get componentProps() {
        const componentProps = { ...this.props.componentProps };
        for (const key of SEARCH_KEYS) {
            componentProps[key] = this.env.searchModel[key];
        }
        componentProps.info = componentProps.info || {};
        for (const key of OTHER_SEARCH_KEYS) {
            componentProps.info[key] = this.env.searchModel[key];
        }
        return componentProps;
    }
}

WithSearch.defaultProps = {
    componentProps: {},
};
WithSearch.props = {
    Component: Function,
    componentProps: { type: Object, optional: true },

    resModel: String,

    globalState: { type: Object, optional: true },

    display: { type: Object, optional: true },

    // search query elements
    comparison: { validate: () => true, optional: true }, // fix problem with validation with type: [Object, null]
    // Issue OWL: https://github.com/odoo/owl/issues/910
    context: { type: Object, optional: true },
    domain: { type: Array, element: [String, Array], optional: true },
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
