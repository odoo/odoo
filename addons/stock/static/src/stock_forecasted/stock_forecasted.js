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
import { Component, onWillStart, useState } from "@odoo/owl";
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

        this.context = useState(this.props.action.context);
        this.productId = this.context.active_id;
        this.resModel = this.context.active_model;
        this.title = this.props.action.name || _t("Forecasted Report");
        if(!this.context.active_id){
            this.context.active_id = this.props.action.params.active_id;
            this.reloadReport();
        }
        this.warehouses = useState([]);
        this.variants = useState([]);

        onWillStart(this._getReportValues);
    }

    get warehouseId() {
        return this.context.warehouse_id;
    }

    get variantId() {
        return this.context.variant_id;
    }

    async _getReportValues() {
        await this._getResModel();
        const variant_id = this.variantId;
        const isTemplate = (!this.resModel || this.resModel === 'product.template' ||
            (this.context.active_model === 'product.template' && !variant_id));
        this.reportModelName = `stock.forecasted_product_${isTemplate ? "template" : "product"}`;
        await this._loadWarehouses();

        if ((isTemplate || this.context.active_model === 'product.template') && this.context.has_variants) {
            await this._loadVariants();
        }
        const reportValues = await this.orm.call(this.reportModelName, "get_report_values", [], {
            context: this.context,
            docids: [(variant_id && variant_id !== 0) ? variant_id : this.productId],
        });
        this.docs = {
            ...reportValues.docs,
            precision: reportValues.precision,
            lead_horizon_date: this.context.lead_horizon_date,
            qty_to_order: this.context.qty_to_order,
        };
    }

    async _getResModel(){
        const variant_id = this.variantId;
        const active_model = this.context.active_model || this.context.params?.active_model;
        this.resModel = variant_id && variant_id !== 0 ? "product.product" : active_model;
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
        const warehouses = await this.orm.searchRead('stock.warehouse', [], ['id', 'name', 'code']);
        this.warehouses = warehouses.length > 1
            ? [{ id: 0, name: _t("All Warehouses") }, ...warehouses]
            : warehouses;

        // If no warehouse ID is set in the context, set a default.
        if (this.warehouseId === undefined) {
            this.updateWarehouse(this.warehouses[0].id);
        }
    }

    async _loadVariants() {
        const variants = await this.orm.searchRead('product.product', [['product_tmpl_id', '=', this.productId]], ['id', 'display_name']);
        this.variants = variants.length > 1
            ? [{ id: 0, display_name: _t("All Variants") }, ...variants]
            : variants;
        // If no variant Id is set in the context, set a default.
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

    get graphDomain() {
        let warehouseIds = [];
        if (this.warehouseId === 0) {
            warehouseIds = this.warehouses.filter(warehouse => warehouse.id > 0).map(warehouse => warehouse.id);
        } else {
            warehouseIds = [this.warehouseId];
        }
        const domain = [
            ["state", "=", "forecast"],
            ["warehouse_id", "in", warehouseIds],
        ];
        if (this.resModel === "product.template") {
            domain.push(["product_tmpl_id", "=", this.productId]);
        } else if (this.resModel === "product.product") {
            const productId = this.context.active_model === 'product.template'
                ? this.variantId
                : this.productId;
            domain.push(["product_id", "=", productId]);
        }
        return domain;
    }

    get graphInfo() {
        return { noContentHelp: _t("Try to add some incoming or outgoing transfers.") };
    }

    get hasStock() {
        return this.docs.product_variants_ids.some((id) => this.docs.product[id].quantity_on_hand > 0);
    }

    async openView(resModel, view, resId=false, domain = false) {
        const action = {
            type: "ir.actions.act_window",
            res_model: resModel,
            views: [[false, view]],
            view_mode: view,
            res_id:  resId,
            domain: domain,
        };
        return this.action.doAction(action);
    }
}

registry.category("actions").add("stock_forecasted", StockForecasted);
