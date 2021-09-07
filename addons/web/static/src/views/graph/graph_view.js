/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { GraphArchParser, MODES, ORDERS } from "./graph_arch_parser";
import { GraphModel } from "./graph_model";
import { GraphRenderer } from "./graph_renderer";
import { GroupByMenu } from "@web/search/group_by_menu/group_by_menu";
import { registry } from "@web/core/registry";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useModel } from "../helpers/model";
import { useService } from "@web/core/utils/hooks";
import { useSetupView } from "@web/views/helpers/view_hook";

const viewRegistry = registry.category("views");

const { Component } = owl;

const KEYS = [
    "additionalMeasures",
    "disableLinking",
    "display",
    "fields",
    "fieldAttrs",
    "groupBy",
    "measure",
    "mode",
    "order",
    "resModel",
    "stacked",
    "title",
    "useSampleModel",
];

export class GraphView extends Component {
    setup() {
        this.actionService = useService("action");

        let modelParams;
        if (this.props.state) {
            modelParams = this.props.state;
        } else {
            const { arch, fields } = this.props;
            const parser = new this.constructor.archParser();
            const archInfo = parser.parse(arch, fields);
            modelParams = {};
            for (const key of KEYS) {
                modelParams[key] = key in archInfo ? archInfo[key] : this.props[key];
            }
        }

        this.model = useModel(this.constructor.Model, modelParams);

        useSetupView({
            exportLocalState: () => this.model.metaData,
            saveParams: () => this.saveParams(),
        });
    }

    /**
     * @param {CustomEvent} ev
     */
    onInspectDomainRecords(ev) {
        const { domain } = ev.detail;
        const { context, resModel, title } = this.model.metaData;

        const views = {};
        for (const [viewId, viewType] of this.props.info.views || []) {
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
     * @returns {Object}
     */
    saveParams() {
        // expand context object? change keys?
        const { measure, groupBy, mode } = this.model.metaData;
        return {
            context: {
                graph_measure: measure,
                graph_mode: mode,
                graph_groupbys: groupBy.map((gb) => gb.spec),
            },
        };
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

GraphView.template = "web.GraphView";
GraphView.buttonTemplate = "web.GraphView.Buttons";

GraphView.components = { ControlPanel, GroupByMenu, Renderer: GraphRenderer, SearchPanel };

GraphView.defaultProps = {
    additionalMeasures: [],
    disableLinking: false,
    display: {},
    measure: "__count",
    mode: "bar",
    order: null,
    stacked: true,
};

GraphView.props = {
    ...standardViewProps,
    additionalMeasures: { type: Array, elements: String, optional: true },
    disableLinking: { type: Boolean, optional: true },
    display: { type: Object, optional: true },
    measure: { type: String, optional: true },
    mode: { validate: (m) => MODES.includes(m), optional: true },
    order: { validate: (o) => ORDERS.includes(o), optional: true },
    stacked: { type: Boolean, optional: true },
    title: { type: String, optional: true },
};

GraphView.type = "graph";

GraphView.display_name = _lt("Graph");
GraphView.icon = "fa-bar-chart";
GraphView.multiRecord = true;

GraphView.Model = GraphModel;

GraphView.archParser = GraphArchParser;

GraphView.searchMenuTypes = ["filter", "groupBy", "comparison", "favorite"];

viewRegistry.add("graph", GraphView);
