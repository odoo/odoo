/** @odoo-module **/

import { formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { patch } from "@web/core/utils/patch";
import {
    QtyAtDatePopover,
    QtyAtDateWidget,
    qtyAtDateWidget,
} from "@sale_stock/widgets/qty_at_date_widget";

patch(QtyAtDatePopover.prototype, {
    async openRentalGanttView() {
        const action = await this.actionService.loadAction("sale_renting.action_rental_order_schedule", this.props.context);
        action.domain = [['product_id', '=', this.props.record.data.product_id[0]]];
        this.actionService.doAction(action, {
            additionalContext: {
                active_model: 'sale.rental.schedule',
                restrict_renting_products: true,
            },
        });
    },
});

patch(QtyAtDateWidget.prototype, {
    updateCalcData() {
        const { data } = this.props.record;
        if (!data.product_id) {
            return;
        }
        if (!data.is_rental || !data.return_date || !data.start_date) {
            return super.updateCalcData();
        }
        this.calcData.stock_end_date = formatDateTime(data.return_date, { format: localization.dateFormat });
        this.calcData.stock_start_date = formatDateTime(data.start_date, { format: localization.dateFormat });
    },
});

export const rentalQtyAtDateWidget = {
    ...qtyAtDateWidget,
    fieldDependencies: [
        { name: 'start_date', type: 'datetime' },
        { name: 'return_date', type: 'datetime' },
    ],
};
patch(qtyAtDateWidget, rentalQtyAtDateWidget);
