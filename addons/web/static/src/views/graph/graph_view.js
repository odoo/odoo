/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { ControlPanel } from "@web/search/control_panel/control_panel";
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
    "fieldModif",
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
            const parser = new GraphArchParser();
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

    get controlPanelProps() {
        const controlPanelProps = Object.assign({}, this.props.info);
        if (this.props.display.controlPanel) {
            controlPanelProps.display = this.props.display.controlPanel;
        }
        return controlPanelProps;
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

GraphView.components = { GroupByMenu };

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
    additionalMeasures: { type: Array, elements: String, optional: 1 },
    disableLinking: { type: Boolean, optional: 1 },
    display: { type: Object, optional: 1 },
    measure: { type: String, optional: 1 },
    mode: { validate: (m) => MODES.includes(m), optional: 1 },
    order: { validate: (o) => ORDERS.includes(o), optional: 1 },
    stacked: { type: Boolean, optional: 1 },
    title: { type: String, optional: 1 },
};

GraphView.type = "graph";

GraphView.display_name = _lt("Graph");
GraphView.icon = "fa-bar-chart";
GraphView.multiRecord = true;

GraphView.Model = GraphModel;
GraphView.Renderer = GraphRenderer;
GraphView.ControlPanel = ControlPanel;

GraphView.searchMenuTypes = ["filter", "groupBy", "comparison", "favorite"];

viewRegistry.add("graph", GraphView);
