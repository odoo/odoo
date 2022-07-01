/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _lt } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";
import { PivotModel } from "@web/views/pivot/pivot_model";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { SearchModel } from "@web/search/search_model";

const viewRegistry = registry.category("views");
const { Component } = owl;

export class PivotView extends Component {
    setup() {
        this.actionService = useService("action");

        let modelParams = {};
        if (this.props.state) {
            modelParams.data = this.props.state.data;
            modelParams.metaData = this.props.state.metaData;
        } else {
            const { arch } = this.props;

            // parse arch
            const archInfo = new this.constructor.ArchParser().parse(arch);

            if (!archInfo.activeMeasures.length || archInfo.displayQuantity) {
                archInfo.activeMeasures.unshift("__count");
            }

            modelParams.metaData = {
                activeMeasures: archInfo.activeMeasures,
                additionalMeasures: this.props.additionalMeasures,
                colGroupBys: archInfo.colGroupBys,
                defaultOrder: archInfo.defaultOrder,
                disableLinking: Boolean(archInfo.disableLinking),
                fields: this.props.fields,
                fieldAttrs: archInfo.fieldAttrs,
                resModel: this.props.resModel,
                rowGroupBys: archInfo.rowGroupBys,
                title: archInfo.title || this.env._t("Untitled"),
                widgets: archInfo.widgets,
            };
        }

        this.model = useModel(this.constructor.Model, modelParams);

        useSetupView({
            getLocalState: () => {
                const { data, metaData } = this.model;
                return { data, metaData };
            },
            getContext: () => this.getContext(),
        });
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
     * @param {Object} param0
     * @param {string} param0.measure
     */
    onMeasureSelected({ measure }) {
        this.model.toggleMeasure(measure);
    }
    /**
     * Execute the action to open the view on the current model.
     *
     * @param {Array} domain
     * @param {Array} views
     * @param {Object} context
     */
    openView(domain, views, context) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.model.metaData.title,
            res_model: this.props.resModel,
            views: views,
            view_mode: "list",
            target: "current",
            context,
            domain,
        });
    }
    /**
     * @param {CustomEvent} ev
     */
    onOpenView(cell) {
        if (cell.value === undefined || this.model.metaData.disableLinking) {
            return;
        }

        const context = Object.assign({}, this.model.searchParams.context);
        Object.keys(context).forEach((x) => {
            if (x === "group_by" || x.startsWith("search_default_")) {
                delete context[x];
            }
        });

        // retrieve form and list view ids from the action
        const { views = [] } = this.env.config;
        this.views = ["list", "form"].map((viewType) => {
            const view = views.find((view) => view[1] === viewType);
            return [view ? view[0] : false, viewType];
        });

        const group = {
            rowValues: cell.groupId[0],
            colValues: cell.groupId[1],
            originIndex: cell.originIndexes[0],
        };
        this.openView(this.model.getGroupDomain(group), this.views, context);
    }
}

class PivotSearchModel extends SearchModel {
    _getIrFilterDescription() {
        this.preparingIrFilterDescription = true;
        const result = super._getIrFilterDescription(...arguments);
        this.preparingIrFilterDescription = false;
        return result;
    }

    _getSearchItemGroupBys(activeItem) {
        const { searchItemId } = activeItem;
        const { context, type } = this.searchItems[searchItemId];
        if (
            !this.preparingIrFilterDescription &&
            type === "favorite" &&
            context.pivot_row_groupby
        ) {
            return context.pivot_row_groupby;
        }
        return super._getSearchItemGroupBys(...arguments);
    }
}

PivotView.template = "web.PivotView";
PivotView.buttonTemplate = "web.PivotView.Buttons";
PivotView.components = { Dropdown, DropdownItem, Renderer: PivotRenderer, Layout };

PivotView.props = {
    ...standardViewProps,
    additionalMeasures: { type: Array, elements: String, optional: 1 },
};
PivotView.defaultProps = {
    additionalMeasures: [],
};

PivotView.Model = PivotModel;
PivotView.SearchModel = PivotSearchModel;

PivotView.ArchParser = PivotArchParser;

PivotView.type = "pivot";
PivotView.display_name = _lt("Pivot");
PivotView.icon = "oi oi-view-pivot";
PivotView.multiRecord = true;
PivotView.searchMenuTypes = ["filter", "groupBy", "comparison", "favorite"];

viewRegistry.add("pivot", PivotView);
