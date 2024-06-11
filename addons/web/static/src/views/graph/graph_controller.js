/** @odoo-module **/

import { Layout } from "@web/search/layout";
import { useModelWithSampleData } from "@web/model/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";

import { Component, useRef } from "@odoo/owl";

export class GraphController extends Component {
    setup() {
        this.model = useModelWithSampleData(this.props.Model, this.props.modelParams);

        useSetupView({
            rootRef: useRef("root"),
            getLocalState: () => {
                return { metaData: this.model.metaData };
            },
            getContext: () => this.getContext(),
        });
        this.searchBarToggler = useSearchBarToggler();
    }

    /**
     * @returns {Object}
     */
    getContext() {
        // expand context object? change keys?
        const { measure, groupBy, mode } = this.model.metaData;
        const context = {
            graph_measure: measure,
            graph_mode: mode,
            graph_groupbys: groupBy.map((gb) => gb.spec),
        };
        if (mode !== "pie") {
            context.graph_order = this.model.metaData.order;
            context.graph_stacked = this.model.metaData.stacked;
            if (mode === "line") {
                context.graph_cumulated = this.model.metaData.cumulated;
            }
        }
        return context;
    }
}

GraphController.template = "web.GraphView";
GraphController.components = { Layout, SearchBar, CogMenu };

GraphController.props = {
    ...standardViewProps,
    Model: Function,
    modelParams: Object,
    Renderer: Function,
    buttonTemplate: String,
};
