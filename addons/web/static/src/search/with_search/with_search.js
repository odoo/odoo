/** @odoo-module **/

import { useBus, useService } from "@web/core/utils/hooks";
import { SearchModel } from "@web/search/search_model";
import { CallbackRecorder, useSetupAction } from "@web/webclient/actions/action_hook";

import { Component, onWillStart, onWillUpdateProps, toRaw, useSubEnv } from "@odoo/owl";

export const SEARCH_KEYS = ["comparison", "context", "domain", "groupBy", "orderBy"];

export class WithSearch extends Component {
    setup() {
        if (!this.env.__getContext__) {
            useSubEnv({ __getContext__: new CallbackRecorder() });
        }
        if (!this.env.__getOrderBy__) {
            useSubEnv({ __getOrderBy__: new CallbackRecorder() });
        }

        const SearchModelClass = this.props.SearchModel || SearchModel;
        this.searchModel = new SearchModelClass(this.env, {
            user: useService("user"),
            orm: useService("orm"),
            view: useService("view"),
        });

        useSubEnv({ searchModel: this.searchModel });

        useBus(this.searchModel, "update", this.render);
        useSetupAction({
            getGlobalState: () => {
                return {
                    searchModel: JSON.stringify(this.searchModel.exportState()),
                };
            },
        });

        onWillStart(async () => {
            const config = { ...toRaw(this.props) };
            if (config.globalState && config.globalState.searchModel) {
                config.state = JSON.parse(config.globalState.searchModel);
                delete config.globalState;
            }
            await this.searchModel.load(config);
        });

        onWillUpdateProps(async (nextProps) => {
            const config = {};
            for (const key of SEARCH_KEYS) {
                if (nextProps[key] !== undefined) {
                    config[key] = nextProps[key];
                }
            }
            await this.searchModel.reload(config);
        });
    }
}

WithSearch.template = "web.WithSearch";
WithSearch.props = {
    slots: Object,
    SearchModel: { type: Function, optional: true },

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
    searchViewId: { type: [Number, Boolean], optional: true },

    irFilters: { type: Array, element: Object, optional: true },
    loadIrFilters: { type: Boolean, optional: true },

    // extra options
    activateFavorite: { type: Boolean, optional: true },
    dynamicFilters: { type: Array, element: Object, optional: true },
    hideCustomGroupBy: { type: Boolean, optional: true },
    searchMenuTypes: { type: Array, element: String, optional: true },
};
