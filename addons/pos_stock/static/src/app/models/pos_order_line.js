import { patch } from "@web/core/utils/patch";
import { range } from "@web/core/utils/numbers";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    get pickingType() {
        return this.models["stock.picking.type"].getFirst();
    },

    getPackLotLinesToEdit(isAllowOnlyOneLot) {
        const currentPackLotLines = this.pack_lot_ids;
        let nExtraLines = Math.abs(this.qty) - currentPackLotLines.length;
        nExtraLines = Math.ceil(nExtraLines);
        nExtraLines = nExtraLines > 0 ? nExtraLines : 1;
        const tempLines = currentPackLotLines
            .map((lotLine) => ({
                id: lotLine.id,
                text: lotLine.lot_name,
            }))
            .concat(range(nExtraLines).map(() => ({ text: "" })));
        return isAllowOnlyOneLot ? [tempLines[0]] : tempLines;
    },

    // What if a number different from 1 (or -1) is specified
    // to an orderline that has product tracked by lot? Lot tracking (based
    // on the current implementation) requires that 1 item per orderline is
    // allowed.
    async editPackLotLines(editedPackLotLines) {
        if (!editedPackLotLines) {
            return;
        }
        this.setPackLotLines(editedPackLotLines);
        this.order_id.selectOrderline(this);
    },

    setPackLotLines({ modifiedPackLotLines, newPackLotLines, setQuantity = true }) {
        const lotLinesToRemove = [];

        for (const lotLine of this.pack_lot_ids) {
            const modifiedLotName = modifiedPackLotLines[lotLine.id];
            if (modifiedLotName) {
                lotLine.lot_name = modifiedLotName;
            } else {
                lotLinesToRemove.push(lotLine);
            }
        }

        // Remove those that needed to be removed.
        for (const lotLine of lotLinesToRemove) {
            lotLine.delete();
        }

        for (const newLotLine of newPackLotLines) {
            this.models["pos.pack.operation.lot"].create({
                lot_name: newLotLine.lot_name,
                pos_order_line_id: this,
            });
        }

        // Set the qty of the line based on number of pack lots.
        if (!this.product_id.to_weight && setQuantity) {
            this.setQuantityByLot();
        }
    },

    setPrice(keep_price) {
        if (!keep_price && this.price_type === "original") {
            const productTemplate = this.product_id.product_tmpl_id;
            if (this.isLotTracked()) {
                const related_lines = [];
                const price = productTemplate.getPrice(
                    this.order_id.pricelist_id,
                    this.getQuantity(),
                    this.getPriceExtra(),
                    false,
                    this.product_id,
                    this,
                    related_lines
                );
                related_lines.forEach((line) => line.setUnitPrice(price));
            } else {
                this.setUnitPrice(
                    productTemplate.getPrice(
                        this.order_id.pricelist_id,
                        this.getQuantity(),
                        this.getPriceExtra(),
                        false,
                        this.product_id
                    )
                );
            }
        }
    },

    setQuantityByLot() {
        var valid_lots_quantity = this.pack_lot_ids.length;
        if (this.qty < 0) {
            valid_lots_quantity = -valid_lots_quantity;
        }
        this.setQuantity(valid_lots_quantity);
    },

    hasValidProductLot() {
        if (this.pack_lot_ids.length > 0) {
            return true;
        }

        const valid_product_lot = this.pack_lot_ids;
        const lotsRequired = this.product_id.tracking == "serial" ? Math.abs(this.qty) : 1;
        return lotsRequired === valid_product_lot.length;
    },

    canBeMergedWith(orderline) {
        const canBeMergedWith = super.canBeMergedWith(orderline);
        const getLotName = (line) => line.pack_lot_ids[0]?.lot_name;
        return (
            canBeMergedWith && (!this.isLotTracked() || getLotName(this) === getLotName(orderline))
        );
    },

    isLotTracked() {
        return (
            this.product_id.tracking === "lot" &&
            (this.pickingType.use_create_lots || this.pickingType.use_existing_lots)
        );
    },

    merge(orderline) {
        super.merge(orderline);
        // Merge pack_lot_ids uniquely to avoid duplicates
        const existingLotNames = new Set(this.pack_lot_ids.map((l) => l.lot_name));
        const uniqueNewLots = orderline.pack_lot_ids.filter(
            (lot) => !existingLotNames.has(lot.lot_name)
        );
        this.update({
            pack_lot_ids: [["link", ...uniqueNewLots]],
        });
    },

    get packLotLines() {
        return this.pack_lot_ids.map(
            (l) =>
                `${l.pos_order_line_id.product_id.tracking == "lot" ? "Lot Number" : "SN"} ${
                    l.lot_name
                }`
        );
    },
});
