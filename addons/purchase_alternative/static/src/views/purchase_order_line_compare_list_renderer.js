import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillStart, useState, useSubEnv } from "@odoo/owl";

export class PurchaseOrderLineCompareListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.bestFields = useState({
                best_price_ids: [],
                best_date_ids: [],
                best_price_unit_ids: [],
        });
        onWillStart(async () => {
            await this.updateBestFields();
        });
        const defaultOnClickViewButton = this.env.onClickViewButton;
        useSubEnv({
            onClickViewButton: async (params) => {
                await defaultOnClickViewButton(params);
                await this.updateBestFields();
            }
        });
    }

    async updateBestFields() {
        [this.bestFields.best_price_ids,
         this.bestFields.best_date_ids,
         this.bestFields.best_price_unit_ids] = await this.props.list.model.orm.call(
            "purchase.order",
            "get_tender_best_lines",
            [this.props.list.context.purchase_order_id || this.props.list.context.active_id],
            { context: this.props.list.context }
        );
    }

    getCellClass(column, record) {
        let classNames = super.getCellClass(...arguments);
        const { resId } = record;
        const isBestPrice = this.bestFields.best_price_ids.includes(resId);
        if (
            (column.name === "price_subtotal" && isBestPrice) ||
            (column.name === "price_total_cc" && isBestPrice) ||
            (column.name === "date_planned" && this.bestFields.best_date_ids.includes(resId)) ||
            (column.name === "price_unit" && this.bestFields.best_price_unit_ids.includes(resId))
        ) {
            classNames += " text-success";
        }
        return classNames;
    }
}
