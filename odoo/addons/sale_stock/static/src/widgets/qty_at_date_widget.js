/** @odoo-module **/

import { formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component, onWillRender } from "@odoo/owl";

export class QtyAtDatePopover extends Component {
    setup() {
        this.actionService = useService("action");
    }

    openForecast() {
        this.actionService.doAction("stock.stock_forecasted_product_product_action", {
            additionalContext: {
                active_model: 'product.product',
                active_id: this.props.record.data.product_id[0],
                warehouse: this.props.record.data.warehouse_id && this.props.record.data.warehouse_id[0],
                move_to_match_ids: this.props.record.data.move_ids.records.map(record => record.resId),
                sale_line_to_match_id: this.props.record.resId,
            },
        });
    }
}

QtyAtDatePopover.template = "sale_stock.QtyAtDatePopover";

export class QtyAtDateWidget extends Component {
    setup() {
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.calcData = {};
        onWillRender(() => {
            this.initCalcData();
        })
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

    showPopup(ev) {
        this.updateCalcData();
        this.popover.open(ev.currentTarget, {
            record: this.props.record,
            calcData: this.calcData,
        });
    }
}

QtyAtDateWidget.components = { Popover: QtyAtDatePopover };
QtyAtDateWidget.template = "sale_stock.QtyAtDate";

export const qtyAtDateWidget = {
    component: QtyAtDateWidget,
};
registry.category("view_widgets").add("qty_at_date_widget", qtyAtDateWidget);
