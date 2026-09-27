import { waitFor } from "@odoo/hoot-dom";
import { clickControlButton } from "@point_of_sale/../tests/unit/ui_utils";

export async function openDiscountPopup() {
    await clickControlButton("Discount");
    await waitFor(".modal .pos-number-popup");
}

export function discountLines(order) {
    return order.lines.filter((line) => line.isDiscountLine);
}
