// @ts-check

/** @module @web/views/pivot/pivot_controller - Controller wiring PivotModel to PivotRenderer with search bar and scroll restoration */

import { Component, useEffect, useRef } from "@odoo/owl";
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
 * Controller for the pivot view.
 *
 * Wires the PivotModel (with sample data support) to the PivotRenderer
 * inside a Layout shell with search bar integration. Restores scroll
 * position from local state and persists pivot-specific context (measures,
 * column/row group-bys) for favorites.
 */
export class PivotController extends Component {
    static template = "web.PivotView";
    static components = { Layout, SearchBar, CogMenu, Widget, ActionHelper };
    static props = {
        ...standardViewProps,
        Model: Function,
        modelParams: Object,
        Renderer: Function,
        buttonTemplate: String,
    };

    /** Initialize the pivot model, action hooks, scroll restoration, and search bar toggler. */
    setup() {
        this.model = useModelWithSampleData(
            this.props.Model,
            this.props.modelParams,
            this.modelOptions,
        );

        const { setScrollFromState } = useSetupAction({
            rootRef: useRef("root"),
            getLocalState: () => {
                const { data, metaData } = this.model;
                return { data, metaData };
            },
            getContext: () => this.getContext(),
        });
        useEffect(
            (isReady) => {
                if (isReady) {
                    setScrollFromState();
                }
            },
            () => [this.model.isReady],
        );
        this.searchBarToggler = useSearchBarToggler();
    }

    /**
     * Whether the "no content" helper should be displayed.
     *
     * True when sample data is active, when the model reports no data,
     * or when no measures are selected.
     *
     * @returns {boolean}
     */
    get displayNoContent() {
        if (this.props.info.noContentHelp === false) {
            return false;
        }
        const { metaData, useSampleModel } = this.model;
        return (
            useSampleModel || !this.model.hasData() || !metaData.activeMeasures.length
        );
    }

    /** @returns {Object} model options derived from env and display props */
    get modelOptions() {
        return /** @type {any} */ (computeModelOptions(this.env, this.props.display));
    }

    /**
     * Build the pivot-specific context for persistence in favorites.
     *
     * @returns {Object}
     */
    getContext() {
        return {
            pivot_measures: this.model.metaData.activeMeasures,
            pivot_column_groupby: this.model.metaData.fullColGroupBys,
            pivot_row_groupby: this.model.metaData.fullRowGroupBys,
        };
    }
}
