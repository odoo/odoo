import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    _captureOldValues(lines) {
        const map = {};
        for (const line of lines) {
            map[line.uuid] = {
                priceExcl: line.priceExcl,
                priceIncl: line.priceIncl,
            };
        }
        return map;
    },

    _updateHistoryLines(lines, oldValues, removedQty, selectedLine) {
        let parentOrderLine;
        if (selectedLine.combo_parent_id) {
            parentOrderLine = selectedLine.combo_parent_id;
        } else if (Object.keys(selectedLine.combo_line_ids).length) {
            parentOrderLine = selectedLine;
        }

        // create parent line first
        let parentHistoryLine = null;
        if (parentOrderLine) {
            parentHistoryLine = this.createHistoryLine(parentOrderLine, oldValues, removedQty);
        }

        for (const line of lines) {
            if (parentOrderLine && line.uuid === parentOrderLine.uuid) {
                continue;
            }
            this.createHistoryLine(line, oldValues, removedQty, parentHistoryLine);
        }
    },

    async updateSelectedOrderline({ buffer, key }) {
        const order = this.pos.getOrder();
        const selectedLine = order.getSelectedOrderline();

        if (
            !this.pos.config.is_history_tracked ||
            (this.pos.numpadMode !== "quantity" && key !== "Backspace")
        ) {
            return await super.updateSelectedOrderline({ buffer, key });
        }

        // Calculate removed quantity
        const removedQty = selectedLine.qty - parseFloat(buffer || 0);
        if (removedQty <= 0) {
            return await super.updateSelectedOrderline({ buffer, key });
        }

        // Get all related lines
        const affectedLines = selectedLine.getAllLinesInCombo();
        // Store old subtotals BEFORE update
        const oldValues = this._captureOldValues(affectedLines);
        const result = await super.updateSelectedOrderline({ buffer, key });
        this._updateHistoryLines(affectedLines, oldValues, removedQty, selectedLine);

        return result;
    },

    createHistoryLine(line, oldValues, removedQty, parentHistoryLine = null) {
        const old = oldValues[line.uuid];

        const removedSubtotal = old.priceExcl - line.priceExcl;
        const removedSubtotalIncl = old.priceIncl - line.priceIncl;

        return this.pos.data.models["pos.history.line"].create({
            product_id: line.product_id,
            qty: removedQty,
            price_unit: line.price_unit,
            combo_item_id: line.combo_item_id,
            price_extra: line.price_extra,
            attribute_value_ids: line.attribute_value_ids,
            custom_attribute_value_ids: line.custom_attribute_value_ids,
            discount: line.discount,
            tax_ids: line.tax_ids,
            order_id: line.order_id,
            price_subtotal: removedSubtotal,
            price_subtotal_incl: removedSubtotalIncl,
            combo_parent_id: parentHistoryLine || undefined,
        });
    },
});
