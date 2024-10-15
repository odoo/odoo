/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { View } from "@web/views/view";
import { ControlPanel } from "@web/search/control_panel/control_panel";

import { ForecastedButtons } from "./forecasted_buttons";
import { ForecastedDetails } from "./forecasted_details";
import { ForecastedHeader } from "./forecasted_header";
import { ForecastedWarehouseFilter } from "./forecasted_warehouse_filter";
import { Component, onWillStart, useState } from "@odoo/owl";

export class StockForecasted extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.context = useState(this.props.action.context);
        this.productId = this.context.active_id;
        this.resModel = this.context.active_model;
        this.title = this.props.action.name || _t("Forecasted Report");
        if(!this.context.active_id){
            this.context.active_id = this.props.action.params.active_id;
            this.reloadReport();
        }
        this.warehouses = useState([]);

        onWillStart(this._getReportValues);
    }

    async _getReportValues() {
        await this._getResModel();
        const isTemplate = !this.resModel || this.resModel === 'product.template';
        this.reportModelName = `stock.forecasted_product_${isTemplate ? "template" : "product"}`;
        this.warehouses.splice(0, this.warehouses.length);
        this.warehouses.push(...await this.orm.searchRead('stock.warehouse', [],['id', 'name', 'code']));
        if (!this.context.warehouse) {
            this.updateWarehouse(this.warehouses[0].id);
        }
        const reportValues = await this.orm.call(this.reportModelName, "get_report_values", [], {
            context: this.context,
            docids: [this.productId],
        });
        this.docs = { ...reportValues.docs, ...reportValues.precision };
    }

    async _getResModel(){
        this.resModel = this.context.active_model || this.context.params?.active_model;
        //Following is used as a fallback when the forecast is not called by an action but through browser's history
        if (!this.resModel) {
            if (this.props.action.res_model) {
                this.resModel = this.props.action.res_model;
            } else if (this.props.action._originalAction) {
                const originalContextAction = JSON.parse(this.props.action._originalAction).context;
                if (typeof originalContextAction === "string") {
                    this.resModel = JSON.parse(originalContextAction.replace(/'/g, '"')).active_model;
                } else if (originalContextAction) {
                    this.resModel = originalContextAction.active_model;
                }
            }
            this.context.active_model = this.resModel;
        }
    }

    async updateWarehouse(id) {
        const hasPreviousValue = this.context.warehouse !== undefined;
        this.context.warehouse = id;
        if (hasPreviousValue) {
            await this.reloadReport();
        }
    }

    async reloadReport() {
        const actionRequest = {
            id: this.props.action.id,
            type: "ir.actions.client",
            tag: "stock_forecasted",
            context: this.context,
            name: this.title,
        };
        const options = { stackPosition: "replaceCurrentAction" };
        return this.action.doAction(actionRequest, options);
    }

    get graphDomain() {
        const warehouseIds = Array.isArray(this.context.warehouse) ? this.context.warehouse : [this.context.warehouse];
        const domain = [
            ["state", "=", "forecast"],
            ["warehouse_id", "in", warehouseIds],
        ];
        if (this.resModel === "product.template") {
            domain.push(["product_tmpl_id", "=", this.productId]);
        } else if (this.resModel === "product.product") {
            domain.push(["product_id", "=", this.productId]);
        }
        return domain;
    }

    get graphInfo() {
        return { noContentHelp: _t("Try to add some incoming or outgoing transfers.") };
    }

    async openView(resModel, view, resId) {
        const action = {
            type: "ir.actions.act_window",
            res_model: resModel,
            views: [[false, view]],
            view_mode: view,
            res_id: resId,
        };
        return this.action.doAction(action);
    }
}

StockForecasted.template = "stock.Forecasted";
StockForecasted.components = {
    ControlPanel,
    ForecastedButtons,
    ForecastedWarehouseFilter,
    ForecastedHeader,
    View,
    ForecastedDetails,
};
registry.category("actions").add("stock_forecasted", StockForecasted);
