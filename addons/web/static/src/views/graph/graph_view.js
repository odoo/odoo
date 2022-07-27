/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { GroupByMenu } from "@web/search/group_by_menu/group_by_menu";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { Layout } from "@web/views/layout";
import { useModel } from "../helpers/model";
import { GraphArchParser } from "./graph_arch_parser";
import { GraphModel } from "./graph_model";
import { GraphRenderer } from "./graph_renderer";
import { SearchModel } from "@web/search/search_model";

const viewRegistry = registry.category("views");

const { Component } = owl;

export class GraphView extends Component {
    setup() {
        this.actionService = useService("action");

        let modelParams;
        if (this.props.state) {
            modelParams = this.props.state.metaData;
        } else {
            const { arch, fields } = this.props;
            const parser = new this.constructor.ArchParser();
            const archInfo = parser.parse(arch, fields);
            modelParams = {
                additionalMeasures: this.props.additionalMeasures,
                disableLinking: Boolean(archInfo.disableLinking),
                displayScaleLabels: this.props.displayScaleLabels,
                fieldAttrs: archInfo.fieldAttrs,
                fields: this.props.fields,
                groupBy: archInfo.groupBy,
                measure: archInfo.measure || "__count",
                mode: archInfo.mode || "bar",
                order: archInfo.order || null,
                resModel: this.props.resModel,
                stacked: "stacked" in archInfo ? archInfo.stacked : true,
                title: archInfo.title || this.env._t("Untitled"),
            };
        }

        this.model = useModel(this.constructor.Model, modelParams);

        useSetupView({
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
     * @param {string} domain the domain of the clicked area
     */
    onGraphClicked(domain) {
        const { context, resModel, title } = this.model.metaData;

        const views = {};
        for (const [viewId, viewType] of this.env.config.views || []) {
            views[viewType] = viewId;
        }
        function getView(viewType) {
            return [views[viewType] || false, viewType];
        }
        const actionViews = [getView("list"), getView("form")];

        this.actionService.doAction(
            {
                context,
                domain,
                name: title,
                res_model: resModel,
                target: "current",
                type: "ir.actions.act_window",
                views: actionViews,
            },
            {
                viewType: "list",
            }
        );
    }

    /**
     * @param {CustomEvent} ev
     */
    onMeasureSelected(ev) {
        const { measure } = ev.detail.payload;
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
}

class GraphSearchModel extends SearchModel {
    _getIrFilterDescription() {
        this.preparingIrFilterDescription = true;
        const result = super._getIrFilterDescription(...arguments);
        this.preparingIrFilterDescription = false;
        return result;
    }

    _getSearchItemGroupBys(activeItem) {
        const { searchItemId } = activeItem;
        const { context, type } = this.searchItems[searchItemId];
        if (!this.preparingIrFilterDescription && type === "favorite" && context.graph_groupbys) {
            return context.graph_groupbys;
        }
        return super._getSearchItemGroupBys(...arguments);
    }
}

GraphView.template = "web.GraphView";
GraphView.buttonTemplate = "web.GraphView.Buttons";

GraphView.components = { GroupByMenu, Renderer: GraphRenderer, Layout };

GraphView.defaultProps = {
    additionalMeasures: [],
    displayGroupByMenu: false,
    displayScaleLabels: true,
};

GraphView.props = {
    ...standardViewProps,
    additionalMeasures: { type: Array, elements: String, optional: true },
    displayGroupByMenu: { type: Boolean, optional: true },
    displayScaleLabels: { type: Boolean, optional: true },
};

GraphView.type = "graph";

GraphView.display_name = _lt("Graph");
GraphView.icon = "fa-bar-chart";
GraphView.multiRecord = true;

GraphView.Model = GraphModel;
GraphView.SearchModel = GraphSearchModel;

GraphView.ArchParser = GraphArchParser;

GraphView.searchMenuTypes = ["filter", "groupBy", "comparison", "favorite"];

viewRegistry.add("graph", GraphView);
