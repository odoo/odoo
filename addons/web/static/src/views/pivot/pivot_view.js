/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { download } from "@web/core/network/download";
import { PivotArchParser } from "./pivot_arch_parser";
import { PivotModel } from "./pivot_model";
import { PivotRenderer } from "./pivot_renderer";
import { registry } from "@web/core/registry";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useModel } from "../helpers/model";
import { useService } from "@web/core/utils/hooks";
import { useSetupView } from "@web/views/helpers/view_hook";

const viewRegistry = registry.category("views");

const { Component } = owl;

export class PivotView extends Component {
    setup() {
        this.actionService = useService("action");

        let modelParams = {};
        if (this.props.state) {
            modelParams.data = this.props.state.data;
            modelParams.meta = this.props.state.meta;
        } else {
            const { arch } = this.props;

            // parse arch
            const archInfo = new PivotArchParser().parse(arch);

            if (!archInfo.activeMeasures.length || archInfo.displayQuantity) {
                archInfo.activeMeasures.unshift("__count");
            }

            modelParams.meta = {
                activeMeasures: archInfo.activeMeasures,
                additionalMeasures: this.props.additionalMeasures,
                colGroupBys: archInfo.colGroupBys,
                defaultOrder: archInfo.defaultOrder,
                disableLinking: Boolean(archInfo.disableLinking),
                fields: this.props.fields,
                fieldAttrs: archInfo.fieldAttrs,
                resModel: this.props.resModel,
                rowGroupBys: archInfo.rowGroupBys,
                title: this.props.title || archInfo.title || this.env._t("Untitled"),
                useSampleModel: Boolean(this.props.useSampleModel),
                widgets: archInfo.widgets,
            };
        }

        this.model = useModel(this.constructor.Model, modelParams);

        useSetupView({
            exportLocalState: () => {
                const { data, meta } = this.model;
                return { data, meta };
            },
            saveParams: () => this.saveParams(), // FIXME: rename this
        });

        this.onOpenView = this.onOpenView.bind(this);
    }
    /**
     * @returns {Object}
     */
    get controlPanelProps() {
        const controlPanelProps = Object.assign({}, this.props.info);
        if (this.props.display.controlPanel) {
            controlPanelProps.display = this.props.display.controlPanel;
        }
        return controlPanelProps;
    }
    /**
     * @returns {Object}
     */
    saveParams() {
        return {
            context: {
                pivot_measures: this.model.meta.activeMeasures,
                pivot_column_groupby: this.model.meta.fullColGroupBys,
                pivot_row_groupby: this.model.meta.fullRowGroupBys,
            },
        };
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Exports the current pivot table data in a xls file. For this, we have to
     * serialize the current state, then call the server /web/pivot/export_xlsx.
     * Force a reload before exporting to ensure to export up-to-date data.
     */
    onDownloadButtonClicked() {
        if (this.model.getTableWidth() > 16384) {
            throw new Error(
                this.env._t(
                    "For Excel compatibility, data cannot be exported if there are more than 16384 columns.\n\nTip: try to flip axis, filter further or reduce the number of measures."
                )
            );
        }
        const table = this.model.exportData();
        download({
            url: "/web/pivot/export_xlsx",
            data: { data: JSON.stringify(table) },
        });
    }
    /**
     * Expands all groups
     */
    onExpandButtonClicked() {
        this.model.expandAll();
    }
    /**
     * Flips axis
     */
    onFlipButtonClicked() {
        this.model.flip();
    }
    /**
     * Toggles the given measure
     *
     * @param {CustomEvent} ev
     */
    onMeasureSelected(ev) {
        this.model.toggleMeasure(ev.detail.payload.measure);
    }
    /**
     * @param {CustomEvent} ev
     */
    onOpenView(cell) {
        if (cell.value === undefined || this.model.meta.disableLinking) {
            return;
        }

        const context = Object.assign({}, this.model.searchParams.context);
        Object.keys(context).forEach((x) => {
            if (x === "group_by" || x.startsWith("search_default_")) {
                delete context[x];
            }
        });

        // retrieve form and list view ids from the action
        this.views = ["list", "form"].map((viewType) => {
            const view = this.props.info.views.find((view) => view[1] === viewType);
            return [view ? view[0] : false, viewType];
        });

        const group = {
            rowValues: cell.groupId[0],
            colValues: cell.groupId[1],
            originIndex: cell.originIndexes[0],
        };
        const domain = this.model.getGroupDomain(group);

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.model.meta.title,
            res_model: this.props.resModel,
            views: this.views,
            view_mode: "list",
            target: "current",
            context,
            domain,
        });
    }
}

PivotView.template = "web.PivotView";
PivotView.buttonTemplate = "web.PivotView.Buttons";

PivotView.props = {
    ...standardViewProps,
    additionalMeasures: { type: Array, elements: String, optional: 1 },
    display: { type: Object, optional: 1 },
    title: { type: String, optional: 1 },
};
PivotView.defaultProps = {
    additionalMeasures: [],
    display: {},
};

PivotView.Model = PivotModel;
PivotView.Renderer = PivotRenderer;
PivotView.ControlPanel = ControlPanel;

PivotView.type = "pivot";
PivotView.display_name = _lt("Pivot");
PivotView.icon = "fa-table";
PivotView.multiRecord = true;
PivotView.searchMenuTypes = ["filter", "groupBy", "comparison", "favorite"];

viewRegistry.add("pivot", PivotView);
