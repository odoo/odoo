import { formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component, onWillRender } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";

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
                active_model: 'product.product',
                active_id: this.props.record.data.product_id.id,
                warehouse_id: this.props.record.data.warehouse_id && this.props.record.data.warehouse_id.id,
                move_to_match_ids: this.props.record.data.move_ids.currentIds,
                sale_line_to_match_id: this.props.record.resId,
            },
        });
    }

    get forecastedLabel() {
        return _t('Forecasted Stock')
    }

    get availableLabel() {
        return _t('Available')
    }
}

export class QtyAtDateWidget extends Component {
    static components = { Popover: QtyAtDatePopover };
    static template = "sale_stock.QtyAtDate";
    static props = {...standardWidgetProps};
    setup() {
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.orm = useService("orm");
        this.calcData = {};
        onWillRender(() => {
            this.initCalcData();
        });
    }

    initCalcData() {
        // calculate data not in record
        const { data } = this.props.record;
        if (data.scheduled_date) {
            // TODO: might need some round_decimals to avoid errors
            if (data.state === 'sale') {
                this.calcData.will_be_fulfilled = data.free_qty_today >= data.qty_to_deliver;
            } else {
                this.calcData.will_be_fulfilled = data.virtual_available_at_date >= data.qty_to_deliver;
            }
            this.calcData.will_be_late = data.forecast_expected_date && data.forecast_expected_date > data.scheduled_date;
            if (['draft', 'sent'].includes(data.state)) {
                // Moves aren't created yet, then the forecasted is only based on virtual_available of quant
                this.calcData.forecasted_issue = !this.calcData.will_be_fulfilled && !data.is_mto;
            } else {
                // Moves are created, using the forecasted data of related moves
                this.calcData.forecasted_issue = !this.calcData.will_be_fulfilled || this.calcData.will_be_late;
            }
        }
    }

    async calcDataForDisplay() {
        const { data } = this.props.record;
        let lineUom;
        if (data.product_uom_id?.[0]) {
            lineUom = (await this.orm.read("uom.uom", [data.product_uom_id[0]], ["factor", "rounding"]))[0];
        }
        let lineProduct;
        if (data.product_id?.[0]) {
            lineProduct = await this.orm.searchRead("product.product", [["id", "=", data.product_id[0]]], ["uom_id"]);
        }
        let productUom;
        if (lineProduct?.[0]?.uom_id?.[0]) {
            productUom = (await this.orm.searchRead("uom.uom", [["id", "=", lineProduct[0].uom_id[0]]], ["factor", "name"]))[0];
        }
        if (lineUom && productUom) {
            this.calcData.product_uom_virtual_available_at_date = roundPrecision(data.virtual_available_at_date * lineUom.factor / productUom.factor, 1);
            this.calcData.product_uom_free_qty_today = roundPrecision(data.free_qty_today * lineUom.factor / productUom.factor, 1);
            this.calcData.product_uom_name = productUom.name;
        }
    }

    updateCalcData() {
        // popup specific data
        const { data } = this.props.record;
        if (!data.scheduled_date) {
            return;
        }
        this.calcData.delivery_date = formatDateTime(data.scheduled_date, { format: localization.dateFormat });
        if (data.forecast_expected_date) {
            this.calcData.forecast_expected_date_str = formatDateTime(data.forecast_expected_date, { format: localization.dateFormat });
        }
    }

    async showPopup(ev) {
        const target = ev.currentTarget;
        await this.calcDataForDisplay();
        this.updateCalcData();
        this.popover.open(target, {
            record: this.props.record,
            calcData: this.calcData,
        });
    }
}

export const qtyAtDateWidget = {
    component: QtyAtDateWidget,
    fieldDependencies: [
        { name: 'display_qty_widget', type: 'boolean'},
        { name: 'free_qty_today', type: 'float'},
        { name: 'forecast_expected_date', type: 'datetime'},
        { name: 'is_mto', type: 'boolean'},
        { name: 'move_ids', type: 'one2many'},
        { name: 'qty_available_today', type: 'float'},
        { name: 'qty_to_deliver', type: 'float'},
        { name: 'scheduled_date', type: 'datetime'},
        { name: 'virtual_available_at_date', type: 'float'},
        { name: 'warehouse_id', type: 'many2one'},
    ],
};
registry.category("view_widgets").add("qty_at_date_widget", qtyAtDateWidget);
