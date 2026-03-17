import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { View } from "@web/views/view";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { Dropdown } from "@web/core/dropdown/dropdown";

import { ForecastedButtons } from "./forecasted_buttons";
import { ForecastedDetails } from "./forecasted_details";
import { ForecastedHeader } from "./forecasted_header";
import { Component, markup, onWillStart, proxy, useProps, usePlugin } from "@odoo/owl";
import { ActionPlugin, standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { ORM } from "@web/core/orm_plugin";

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
        this.orm = usePlugin(ORM);
        this.action = usePlugin(ActionPlugin);

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

    updateVariant(id) {
        this.context.variant_id = id;
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

    _dropdownItems(allLabel, records, selectedId, onSelect) {
        return [{ id: 0, display_name: allLabel }, ...records].map((record) => ({
            id: record.id,
            label: record.display_name,
            class: { selected: record.id === selectedId },
            onSelected: () => onSelect(record.id),
        }));
    }

    get variantId() {
        return this.context.variant_id || 0;
    }

    get warehousesItems() {
        return this._dropdownItems(_t("All Warehouses"), this.docs.warehouses, this.warehouseId, (id) =>
            this.updateWarehouse(id)
        );
    }

    get variantItems() {
        return this._dropdownItems(_t("All Variants"), this.docs.product_variants, this.variantId, (id) =>
            this.updateVariant(id)
        );
    }

    get activeWarehouseName() {
        return this.warehousesItems.find((item) => item.id === this.warehouseId)?.label;
    }

    get activeVariantName() {
        return this.variantItems.find((item) => item.id === this.variantId)?.label;
    }

    get filteredDocs() {
        const warehouse = this.warehouseId;
        const variant = this.variantId;

        if (!variant && !warehouse) {
            return this.docs;
        }
        return{
            ...this.docs,
            lines: this.docs.lines.filter(
                (l) =>
                    (!variant || l.product.id === variant) &&
                    (!warehouse || l.warehouse_id === warehouse)
            ),
            product: Object.fromEntries(
                Object.entries(this.docs.product).filter(([key]) => {
                    const [productId, warehouseId] = key.split("_").map(Number);
                    return (
                        (!variant || productId === variant) &&
                        (!warehouse || warehouseId === warehouse)
                    );
                })
            ),
            multiple_product: !variant,
            multiple_warehouses: !warehouse,
            warehouse_ids: warehouse ? [warehouse] : this.docs.warehouse_ids,
            product_variants_ids: variant ? [variant] : this.docs.product_variants_ids,
        };
    }

    get graphDomain() {
        const filteredDocs = this.filteredDocs;
        return [
            ["state", "=", "forecast"],
            ["warehouse_id", "in", filteredDocs.warehouse_ids],
            ["product_id", "in", filteredDocs.product_variants_ids],
        ];
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

    getForecastedButtonsProps() {
        return {
            context: this.context,
            reloadReport: this.reloadReport.bind(this),
        };
    }
}

registry.category("actions").add("stock_forecasted", StockForecasted);
