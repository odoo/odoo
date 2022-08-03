/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { GroupByMenu } from "@web/search/group_by_menu/group_by_menu";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";

const { Component, useRef } = owl;

export class GraphController extends Component {
    setup() {
        this.actionService = useService("action");
        this.model = useModel(this.props.Model, this.props.modelParams);

        useSetupView({
            rootRef: useRef("root"),
            getLocalState: () => {
                return { metaData: this.model.metaData };
            },
            getContext: () => this.getContext(),
        });
    }

    /**
     * @returns {Object}
     */
    getContext() {
        // expand context object? change keys?
        const { measure, groupBy, mode } = this.model.metaData;
        return {
            graph_measure: measure,
            graph_mode: mode,
            graph_groupbys: groupBy.map((gb) => gb.spec),
        };
    }

    /**
     * Execute the action to open the view on the current model.
     *
     * @param {Array} domain
     * @param {Array} views
     * @param {Object} context
     */
    openView(domain, views, context) {
        this.actionService.doAction(
            {
                context,
                domain,
                name: this.model.metaData.title,
                res_model: this.model.metaData.resModel,
                target: "current",
                type: "ir.actions.act_window",
                views,
            },
            {
                viewType: "list",
            }
        );
    }
    /**
     * @param {string} domain the domain of the clicked area
     */
    onGraphClicked(domain) {
        const { context } = this.model.metaData;

        Object.keys(context).forEach((x) => {
            if (x === "group_by" || x.startsWith("search_default_")) {
                delete context[x];
            }
        });

        const views = {};
        for (const [viewId, viewType] of this.env.config.views || []) {
            views[viewType] = viewId;
        }
        function getView(viewType) {
            return [views[viewType] || false, viewType];
        }
        const actionViews = [getView("list"), getView("form")];
        this.openView(domain, actionViews, context);
    }

    /**
     * @param {Object} param0
     * @param {string} param0.measure
     */
    onMeasureSelected({ measure }) {
        this.model.updateMetaData({ measure });
    }

    /**
     * @param {"bar"|"line"|"pie"} mode
     */
    onModeSelected(mode) {
        this.model.updateMetaData({ mode });
    }

    /**
     * @param {"ASC"|"DESC"} order
     */
    toggleOrder(order) {
        const { order: currentOrder } = this.model.metaData;
        const nextOrder = currentOrder === order ? null : order;
        this.model.updateMetaData({ order: nextOrder });
    }

    toggleStacked() {
        const { stacked } = this.model.metaData;
        this.model.updateMetaData({ stacked: !stacked });
    }

    toggleCumulated() {
        const { cumulated } = this.model.metaData;
        this.model.updateMetaData({ cumulated: !cumulated });
    }
}

GraphController.template = "web.GraphView";
GraphController.components = { Dropdown, DropdownItem, GroupByMenu, Layout };

GraphController.defaultProps = {
    additionalMeasures: [],
    displayGroupByMenu: false,
    displayScaleLabels: true,
};

GraphController.props = {
    ...standardViewProps,
    additionalMeasures: { type: Array, elements: String, optional: true },
    displayGroupByMenu: { type: Boolean, optional: true },
    displayScaleLabels: { type: Boolean, optional: true },
    Model: Function,
    modelParams: Object,
    Renderer: Function,
    buttonTemplate: String,
};
