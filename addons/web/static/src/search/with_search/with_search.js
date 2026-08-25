import { render, useSubEnv } from "@web/owl2/utils";
import { Component, onWillStart, onWillUpdateProps, t, toRaw, useProps } from "@odoo/owl";
import { CallbackRecorder, useSetupAction } from "@web/search/action_hook";
import { SearchModel } from "@web/search/search_model";
import { useBus, useService } from "@web/core/utils/hooks";

export const SEARCH_KEYS = ["context", "domain", "groupBy", "orderBy"];

export const withSearchProps = {
    slots: t.object(),
    SearchModel: t.function().optional(),

    resModel: t.string(),

    globalState: t.object().optional(),
    urlState: t.object().optional(),
    searchModelArgs: t.object().optional(),

    display: t.object().optional(),

    // search query elements
    context: t.object().optional(),
    domain: t.array(t.or([t.string(), t.array()])).optional(),
    groupBy: t.array(t.string()).optional(),
    orderBy: t.array(t.object()).optional(),

    // search view description
    searchViewArch: t.string().optional(),
    searchViewFields: t.object().optional(),
    searchViewId: t.or([t.number(), t.boolean()]).optional(),

    irFilters: t.array(t.object()).optional(),
    loadIrFilters: t.boolean().optional(),

    // extra options
    activateFavorite: t.boolean().optional(),
    dynamicFilters: t.array(t.object()).optional(),
    hideCustomGroupBy: t.boolean().optional(),
    searchMenuTypes: t.array(t.string()).optional(),
    canOrderByCount: t.boolean().optional(),
    defaultGroupBy: t.array(t.string()).optional(),
};

export class WithSearch extends Component {
    static template = "web.WithSearch";
    props = useProps(withSearchProps);

    setup() {
        if (!this.env.__getContext__) {
            useSubEnv({ __getContext__: new CallbackRecorder() });
        }
        if (!this.env.__getOrderBy__) {
            useSubEnv({ __getOrderBy__: new CallbackRecorder() });
        }

        const SearchModelClass = this.props.SearchModel || SearchModel;
        this.searchModel = new SearchModelClass(
            this.env,
            {
                orm: useService("orm"),
                view: useService("view"),
                field: useService("field"),
                name: useService("name"),
                dialog: useService("dialog"),
                treeProcessor: useService("tree_processor"),
            },
            this.props.searchModelArgs
        );

        const searchPanelState = this.props.globalState?.searchPanel
            ? JSON.parse(this.props.globalState?.searchPanel)
            : null;
        useSubEnv({ searchModel: this.searchModel, searchPanelState });

        useBus(this.searchModel, "update", () => render(this));
        useSetupAction({
            getGlobalState: () => ({
                searchModel: JSON.stringify(this.searchModel.exportState()),
            }),
        });

        onWillStart(async () => {
            // owl3 exposes every declared prop, including those the parent did
            // not pass. Only forward the ones actually provided: the search
            // model distinguishes a missing key from an undefined value (e.g.
            // `"activateFavorite" in config`).
            const config = {};
            for (const [key, value] of Object.entries(toRaw(this.props))) {
                if (value !== undefined) {
                    config[key] = value;
                }
            }
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
