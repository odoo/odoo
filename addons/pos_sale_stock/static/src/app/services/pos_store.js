import { _t } from "@web/core/l10n/translation";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async updateSOLines(line, convertedLine, newLine, newLineValues, state) {
        if (
            ["lot", "serial"].includes(newLine.getProduct().tracking) &&
            (this.pickingType.use_create_lots || this.pickingType.use_existing_lots) &&
            convertedLine.lot_names.length > 0
        ) {
            if (!state.useLoadedLots && !state.userWasAskedAboutLoadedLots) {
                state.useLoadedLots = await ask(this.dialog, {
                    title: _t("SN/Lots Loading"),
                    body: _t("Do you want to load the SN/Lots linked to the Sales Order?"),
                    cancelLabel: _t("Discard"),
                });
                state.userWasAskedAboutLoadedLots = true;
            }
            if (state.useLoadedLots) {
                newLine.setPackLotLines({
                    modifiedPackLotLines: [],
                    newPackLotLines: (convertedLine.lot_names || []).map((name) => ({
                        lot_name: name,
                    })),
                });
            }
        }
        await super.updateSOLines(...arguments);
    },
    splitSOLine(line, convertedLine, newLine, newLineValues, state) {
        const splittedOrderLines = super.splitSOLine(...arguments);
        if (line.product_id.tracking !== "lot") {
            return splittedOrderLines;
        }

        const lotSplittedLines = splittedOrderLines.filter(
            (line) => line.product_id.tracking === "lot"
        );
        // Order line can only hold one lot, so assign lots to individual split lines
        if (
            line.product_id.tracking == "lot" &&
            convertedLine.lot_names.length > 0 &&
            state.useLoadedLots
        ) {
            const priceUnit = newLine.price_unit;
            newLine.delete();
            let total_lot_quantity = 0;
            for (const lot of convertedLine.lot_names) {
                let lot_remaining_quantity = convertedLine.lot_qty_by_name[lot] || 0;
                while (lotSplittedLines.length && lot_remaining_quantity > 0) {
                    const splitted_line = lotSplittedLines.shift();
                    splitted_line.setPackLotLines({
                        modifiedPackLotLines: [],
                        newPackLotLines: [{ lot_name: lot }],
                        setQuantity: false,
                    });
                    total_lot_quantity += splitted_line.qty;
                    lot_remaining_quantity -= splitted_line.qty;
                }
                if (lot_remaining_quantity > 0 && lotSplittedLines.length == 0) {
                    const splitted_line = this.models["pos.order.line"].create({
                        ...newLineValues,
                    });
                    splitted_line.setQuantity(lot_remaining_quantity, true);
                    splitted_line.setUnitPrice(priceUnit);
                    splitted_line.setDiscount(line.discount);
                    splitted_line.setPackLotLines({
                        modifiedPackLotLines: [],
                        newPackLotLines: [{ lot_name: lot }],
                        setQuantity: false,
                    });
                    total_lot_quantity += lot_remaining_quantity;
                }
            }
            if (total_lot_quantity < newLineValues.qty && lotSplittedLines.length == 0) {
                const splitted_line = this.models["pos.order.line"].create({
                    ...newLineValues,
                });
                splitted_line.setQuantity(newLineValues.qty - total_lot_quantity, true);
                splitted_line.setDiscount(line.discount);
            }
        }
        return splittedOrderLines;
    },
    initLoadState() {
        return {
            ...super.initLoadState(),
            useLoadedLots: false,
            userWasAskedAboutLoadedLots: false,
        };
    },
});
