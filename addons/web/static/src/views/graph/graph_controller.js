// @ts-check

/** @module @web/views/graph/graph_controller - Controller wiring GraphModel to GraphRenderer with search bar and sample data support */

import { Component, useRef } from "@odoo/owl";
import { useModelWithSampleData } from "@web/model/model";
import { useSetupAction } from "@web/search/action_hook";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { Layout } from "@web/search/layout";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { ActionHelper } from "@web/views/action_helper";
import { standardViewProps } from "@web/views/standard_view_props";
import { computeModelOptions } from "@web/views/view_utils";
import { Widget } from "@web/views/widgets/widget";

/**
 * Controller for the graph view.
 *
 * Wires the GraphModel (with sample data support) to the GraphRenderer
 * inside a Layout shell with search bar integration. Persists graph-specific
 * context (measure, mode, groupBy, order, stacked, cumulated) for favorites.
 */
export class GraphController extends Component {
    static template = "web.GraphView";
    static components = { Layout, SearchBar, CogMenu, Widget, ActionHelper };
    static props = {
        ...standardViewProps,
        Model: Function,
        modelParams: Object,
        Renderer: Function,
        buttonTemplate: String,
    };

    /** Initialize the graph model, action hooks, and search bar toggler. */
    setup() {
        this.model = useModelWithSampleData(
            this.props.Model,
            this.props.modelParams,
            this.modelOptions,
        );

        useSetupAction({
            rootRef: useRef("root"),
            getLocalState: () => ({ metaData: this.model.metaData }),
            getContext: () => this.getContext(),
        });
        this.searchBarToggler = useSearchBarToggler();
    }

    /** @returns {Object} model options derived from env and display props */
    get modelOptions() {
        return /** @type {any} */ (computeModelOptions(this.env, this.props.display));
    }

    /**
     * Build the graph-specific context for persistence in favorites.
     *
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
