import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { View } from "@web/views/view";
import { ControlPanel } from "@web/search/control_panel/control_panel";

import { ForecastedButtons } from "./forecasted_buttons";
import { ForecastedDetails } from "./forecasted_details";
import { ForecastedHeader } from "./forecasted_header";
import { ForecastedWarehouseFilter } from "./forecasted_warehouse_filter";
import { ForecastedProductVariantFilter } from "./forecasted_product_variant_filter";
import { Component, markup, onWillStart, proxy } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class StockForecasted extends Component {
    static template = "stock.Forecasted";
    static components = {
        ControlPanel,
        ForecastedButtons,
        ForecastedWarehouseFilter,
        ForecastedProductVariantFilter,
        ForecastedHeader,
        View,
        ForecastedDetails,
    };
    static props = { ...standardActionServiceProps };
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.context = proxy(this.props.action.context);
        this.productId = this.context.active_id;
        this.resModel = this.variantId ? "product.product" : this.context.active_model;
        this.title = this.props.action.name || _t("Forecasted Report");
        if(!this.context.active_id){
            this.context.active_id = this.props.action.params.active_id;
            this.reloadReport();
        }
        this.warehouses = proxy([]);
        this.variants = proxy([]);

        onWillStart(this._getReportValues);
    }

    async _getReportValues() {
        await this._getResModel();
        const isTemplate = !this.resModel || this.resModel === 'product.template';
        this.reportModelName = `stock.forecasted_product_${isTemplate ? "template" : "product"}`;
        await this._loadWarehouses();
        if (this.context.has_variants) {
            await this._loadVariants();
        }
        const reportValues = await this.orm.call(this.reportModelName, "get_report_values", [], {
            context: this.context,
            docids: [this.variantId || this.productId],
        });
        this.docs = {
            ...reportValues.docs,
            precision: reportValues.precision,
            lead_horizon_date: this.context.lead_horizon_date,
            qty_to_order: this.context.qty_to_order,
        };
    }

    async _getResModel(){
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

    async _loadWarehouses() {
        const warehouses = await this.orm.searchRead("stock.warehouse", [], ["id", "name"]);
        this.warehouses =
            warehouses.length > 1
                ? [{ id: 0, name: _t("All Warehouses") }, ...warehouses]
                : warehouses;

        // If no warehouse is selected by the user, set a default.
        if (this.warehouseId === undefined) {
            this.updateWarehouse(this.warehouses[0].id);
        }
    }

    async _loadVariants() {
        const variants = await this.orm.searchRead(
            "product.product",
            [["product_tmpl_id", "=", this.productId]],
            ["id", "display_name"]
        );
        this.variants = [{ id: 0, display_name: _t("All Variants") }, ...variants];

        // If no variant is selected by the user, set a default.
        if (this.variantId === undefined) {
            this.updateVariant(this.variants[0].id);
        }
    }

    async updateWarehouse(id) {
        const hasPreviousValue = this.warehouseId !== undefined;
        this.context.warehouse_id = id;
        if (hasPreviousValue) {
            await this.reloadReport();
        }
    }

    async updateVariant(id) {
        const hasPreviousValue = this.variantId !== undefined;
        this.context.variant_id = id;
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

    get warehouseId() {
        return this.context.warehouse_id;
    }

    get variantId() {
        return this.context.variant_id;
    }

    get selectedWarehouseIds() {
        return this.warehouseId === 0
            ? this.warehouses.filter(({ id }) => id > 0).map(({ id }) => id)
            : [this.warehouseId];
    }

    get graphDomain() {
        const domain = [
            ["state", "=", "forecast"],
            ["warehouse_id", "in", this.selectedWarehouseIds],
        ];
        if (this.resModel === "product.template") {
            domain.push(["product_tmpl_id", "=", this.productId]);
        } else if (this.resModel === "product.product") {
            domain.push([
                "product_id",
                "=",
                this.context.active_model === "product.template" ? this.variantId : this.productId,
            ]);
        }
        return domain;
    }

    get graphInfo() {
        return {
            noContentHelp: markup(`<span class="text-muted">${_t("No History Yet")}</span>`),
        };
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
