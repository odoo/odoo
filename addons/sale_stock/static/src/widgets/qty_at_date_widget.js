/** @odoo-module native */
import { Component } from "@odoo/owl";
import { formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { roundPrecision } from "@web/core/utils/format/numbers";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/ui/popover";
import { standardWidgetProps } from "@web/views/widgets";

export class QtyAtDatePopover extends Component {
    static template = "sale_stock.QtyAtDatePopover";
    static props = {
        record: Object,
        calcData: Object,
        close: Function,
    };
    setup() {
        this.actionService = useService("action");
    }

    openForecast() {
        this.actionService.doAction("stock.stock_forecasted_product_product_action", {
            additionalContext: {
                active_model: "product.product",
                active_id: this.props.record.data.product_id.id,
                warehouse_id:
                    this.props.record.data.warehouse_id &&
                    this.props.record.data.warehouse_id.id,
                move_to_match_ids: this.props.record.data.move_ids.currentIds,
                sale_line_to_match_id: this.props.record.resId,
            },
        });
    }

    get forecastedLabel() {
        return _t("Forecasted Stock");
    }

    get availableLabel() {
        return _t("Available");
    }
}

export class QtyAtDateWidget extends Component {
    static components = { Popover: QtyAtDatePopover };
    static template = "sale_stock.QtyAtDate";
    static props = { ...standardWidgetProps };
    static uomCache = new Map();
    setup() {
        this.popover = usePopover(this.constructor.components.Popover, {
            position: "top",
        });
        this.orm = useService("orm");
        this._calcData = {};
    }

    get calcData() {
        this.initCalcData();
        return this._calcData;
    }

    initCalcData() {
        const { data } = this.props.record;
        if (data.date_planned) {
            if (data.state === "done") {
                this._calcData.will_be_fulfilled =
                    data.qty_free_today >= data.qty_to_transfer;
            } else {
                this._calcData.will_be_fulfilled =
                    data.qty_available_virtual_at_date >= data.qty_to_transfer;
            }
            this._calcData.will_be_late =
                data.date_planned_forecast &&
                data.date_planned_forecast > data.date_planned;
            if (data.state === "draft") {
                this._calcData.forecasted_issue =
                    !this._calcData.will_be_fulfilled && !data.is_mto;
            } else {
                this._calcData.forecasted_issue =
                    !this._calcData.will_be_fulfilled || this._calcData.will_be_late;
            }
        }
    }

    async updateCalcDataQuantities() {
        const { data } = this.props.record;
        const lineUomId = data.product_uom_id?.[0];
        const productId = data.product_id?.[0];
        if (!lineUomId || !productId) {
            return;
        }
        const cacheKey = `${productId}/${lineUomId}`;
        let factors = this.constructor.uomCache.get(cacheKey);
        if (!factors) {
            const [product] = await this.orm.read(
                "product.product",
                [productId],
                ["uom_id"],
            );
            const productUomId = product?.uom_id?.[0];
            if (!productUomId) {
                return;
            }
            const uoms = await this.orm.read(
                "uom.uom",
                [...new Set([lineUomId, productUomId])],
                ["factor", "name"],
            );
            const byId = Object.fromEntries(uoms.map((u) => [u.id, u]));
            if (!byId[lineUomId] || !byId[productUomId]) {
                return;
            }
            factors = {
                lineFactor: byId[lineUomId].factor,
                productFactor: byId[productUomId].factor,
                productName: byId[productUomId].name,
            };
            this.constructor.uomCache.set(cacheKey, factors);
        }
        const ratio = factors.lineFactor / factors.productFactor;
        this.calcData.product_uom_qty_available_virtual_at_date = roundPrecision(
            data.qty_available_virtual_at_date * ratio,
            1,
        );
        this.calcData.product_uom_qty_free_today = roundPrecision(
            data.qty_free_today * ratio,
            1,
        );
        this.calcData.product_uom_name = factors.productName;
    }

    updateCalcDataDates() {
        const { data } = this.props.record;
        if (!data.date_planned) {
            return;
        }
        this.calcData.delivery_date = formatDateTime(data.date_planned, {
            format: localization.dateFormat,
        });
        if (data.date_planned_forecast) {
            this.calcData.date_planned_forecast_str = formatDateTime(
                data.date_planned_forecast,
                { format: localization.dateFormat },
            );
        }
    }

    async showPopup(ev) {
        const target = ev.currentTarget;
        await this.updateCalcDataQuantities();
        this.updateCalcDataDates();
        this.popover.open(target, {
            record: this.props.record,
            calcData: this.calcData,
        });
    }
}

export const qtyAtDateWidget = {
    component: QtyAtDateWidget,
    fieldDependencies: [
        { name: "display_qty_widget", type: "boolean" },
        { name: "qty_free_today", type: "float" },
        { name: "date_planned_forecast", type: "datetime" },
        { name: "is_mto", type: "boolean" },
        { name: "move_ids", type: "one2many" },
        { name: "qty_available_today", type: "float" },
        { name: "qty_to_transfer", type: "float" },
        { name: "date_planned", type: "datetime" },
        { name: "qty_available_virtual_at_date", type: "float" },
        { name: "warehouse_id", type: "many2one" },
    ],
};
registry.category("view_widgets").add("qty_at_date_widget", qtyAtDateWidget);
