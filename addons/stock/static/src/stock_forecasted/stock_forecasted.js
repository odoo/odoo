import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { View } from "@web/views/view";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { Dropdown } from "@web/core/dropdown/dropdown";

import { ForecastedButtons } from "./forecasted_buttons";
import { ForecastedDetails } from "./forecasted_details";
import { ForecastedHeader } from "./forecasted_header";
import { Component, onWillStart, proxy, useProps } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

export class StockForecasted extends Component {
    static template = "stock.Forecasted";
    static components = {
        ControlPanel,
        ForecastedButtons,
        Dropdown,
        ForecastedHeader,
        View,
        ForecastedDetails,
    };
    props = useProps(standardActionServiceProps);
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.context = proxy(this.props.action.context);
        this.productId = this.context.active_id;
        this.resModel = this.context.active_model;
        this.title = this.props.action.name || _t("Forecasted Report");
        if(!this.context.active_id){
            this.context.active_id = this.props.action.params.active_id;
            this.reloadReport();
        }

        onWillStart(this._getReportValues);
    }

    async _getReportValues() {
        await this._getResModel();
        const isTemplate = !this.resModel || this.resModel === 'product.template';
        this.reportModelName = `stock.forecasted_product_${isTemplate ? "template" : "product"}`;
        const reportValues = await this.orm.call(this.reportModelName, "get_report_values", [], {
            context: this.context,
            docids: [this.productId],
        });
        this.docs = {
            ...reportValues.docs,
            precision: reportValues.precision,
            lead_horizon_date: this.context.lead_horizon_date,
            qty_to_order: this.context.qty_to_order,
        };
    }

    async _getResModel(){
        this.resModel = this.context.active_model || this.context.params?.active_model;
        //Following is used as a fallback when the forecast is not called by an action but through browser's history
        if (!this.resModel) {
            let resModel = this.props.action.res_model;
            if (resModel) {
                if (/^\d+$/.test(resModel)) {
                    // legacy action definition where res_model is the model id instead of name
                    const actionModel = await this.orm.read('ir.model', [Number(resModel)], ['model']);
                    resModel = actionModel[0]?.model;
                }
                this.resModel = resModel;
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

    updateWarehouse(id) {
        this.context.warehouse_id = id;
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

    get warehouseId() {
        return this.context.warehouse_id || 0;
    }

    get warehousesItems() {
        return [{ id: 0, display_name: "All Warehouses" }, ...this.docs.warehouses].map(
            (warehouse) => ({
                id: warehouse.id,
                label: warehouse.display_name,
                class: { selected: warehouse.id === this.warehouseId },
                onSelected: () => this.updateWarehouse(warehouse.id),
            })
        );
    }

    get activeWarehouseName() {
        return this.warehouseId === 0
            ? _t("All Warehouses")
            : this.docs.warehouses.find((warehouse) => warehouse.id === this.warehouseId)
                  ?.display_name;
    }

    get filteredDocs() {
        const { warehouse_id: warehouse } = this.context;

        if (!warehouse) {
            return this.docs;
        }

        return {
            ...this.docs,
            lines: this.docs.lines.filter((l) => l.warehouse_id === warehouse),
            product: Object.fromEntries(
                Object.entries(this.docs.product).filter(([key]) => {
                    const [, warehouseId] = key.split("_").map(Number);
                    return warehouseId === warehouse;
                })
            ),
            multiple_warehouses: !warehouse,
            warehouse_ids: [warehouse],
        };
    }

    get selectedWarehouseIds() {
        return this.warehouseId === 0
            ? this.warehouses.filter(({ id }) => id > 0).map(({ id }) => id)
            : [this.warehouseId];
    }

    get graphDomain() {
        const domain = [
            ["state", "=", "forecast"],
            ["warehouse_id", "in", this.filteredDocs.warehouse_ids],
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

    async openView(resModel, view, resId=false, domain = false) {
        const views = [[false, view]];
        if (view !== "form") {
            views.push([false, "form"]);
        }
        const action = {
            type: "ir.actions.act_window",
            res_model: resModel,
            views,
            view_mode: view,
            res_id:  resId,
            domain: domain,
        };
        return this.action.doAction(action);
    }
}

registry.category("actions").add("stock_forecasted", StockForecasted);
