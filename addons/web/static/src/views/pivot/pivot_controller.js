import { Layout } from "@web/search/layout";
import { useModelWithSampleData } from "@web/model/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupAction } from "@web/search/action_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { Widget } from "@web/views/widgets/widget";
import { ActionHelper } from "@web/views/action_helper";

import { Component, useEffect, useRef } from "@odoo/owl";

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

    setup() {
        this.model = useModelWithSampleData(
            this.props.Model,
            this.props.modelParams,
            this.modelOptions
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
            () => [this.model.isReady]
        );
        this.searchBarToggler = useSearchBarToggler();
    }

    get displayNoContent() {
        if (this.props.info.noContentHelp === false) {
            return false;
        }
        const { metaData, useSampleModel } = this.model;
        return useSampleModel || !this.model.hasData() || !metaData.activeMeasures.length;
    }

    get modelOptions() {
        return {
            lazy:
                !this.env.config.isReloadingController &&
                !this.env.inDialog &&
                !!this.props.display.controlPanel,
        };
    }

    /**
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
