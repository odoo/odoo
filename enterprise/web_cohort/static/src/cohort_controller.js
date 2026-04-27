/* @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { useModelWithSampleData } from "@web/model/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupAction } from "@web/search/action_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { CogMenu } from "@web/search/cog_menu/cog_menu";

import { Component, toRaw, useRef } from "@odoo/owl";

export class CohortController extends Component {
    static template = "web_cohort.CohortView";
    static components = { Layout, SearchBar, CogMenu };
    static props = {
        ...standardViewProps,
        Model: Function,
        modelParams: Object,
        Renderer: Function,
        buttonTemplate: String,
    };

    setup() {
        this.actionService = useService("action");
        this.model = useModelWithSampleData(this.props.Model, toRaw(this.props.modelParams));

        useSetupAction({
            rootRef: useRef("root"),
            getLocalState: () => {
                return { metaData: this.model.metaData };
            },
            getContext: () => this.getContext(),
        });
    }

    getContext() {
        const { measure, interval } = this.model.metaData;
        return { cohort_measure: measure, cohort_interval: interval };
    }

    /**
     * @param {Object} row
     */
    onRowClicked(row) {
        if (row.value === undefined || this.model.metaData.disableLinking) {
            return;
        }

        const context = Object.assign({}, this.model.searchParams.context);
        const domain = row.domain;
        const views = {};
        for (const [viewId, viewType] of this.env.config.views || []) {
            views[viewType] = viewId;
        }
        function getView(viewType) {
            return [context[`${viewType}_view_id`] || views[viewType] || false, viewType];
        }
        const actionViews = [getView("list"), getView("form")];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.model.metaData.title,
            res_model: this.model.metaData.resModel,
            views: actionViews,
            view_mode: "list",
            target: "current",
            context: context,
            domain: domain,
        });
    }
}
