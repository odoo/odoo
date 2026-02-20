import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateLineData() {
        return this.order.lines.map((line) => {
            const productData = { ...line.product_id.raw };
            productData.display_name = line.getFullProductName();

            return {
                ...line.raw,
                product_data: productData,
                product_uom_name: line.product_id.uom_id?.name || "",
                unit_price: line.currencyDisplayPriceUnit,
                product_unit_price: line.product_id.displayPriceUnit,
                price_subtotal_incl: line.currencyDisplayPrice,
                lot_names: line.pack_lot_ids?.length
                    ? line.pack_lot_ids.map((l) => l.lot_name)
                    : false,
            };
        });
    },
});
