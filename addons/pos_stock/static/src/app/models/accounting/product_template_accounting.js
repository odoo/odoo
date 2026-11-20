import { ProductTemplateAccounting } from "@point_of_sale/app/models/accounting/product_template_accounting";
import { patch } from "@web/core/utils/patch";

patch(ProductTemplateAccounting.prototype, {
    getPrice(
        pricelist,
        quantity,
        price_extra = 0,
        recurring = false,
        variant = false,
        original_line = false,
        related_lines = [],
        uom = false
    ) {
        if (original_line && original_line.isLotTracked() && variant) {
            related_lines.push(
                ...original_line.order_id.lines.filter(
                    (line) =>
                        line.product_id.id == variant.id &&
                        line.product_uom_id.id === original_line.product_uom_id.id
                )
            );
            quantity = related_lines.reduce((sum, line) => sum + line.getQuantity(), 0);
            uom = original_line.product_uom_id;
        }
        return super.getPrice(
            pricelist,
            quantity,
            price_extra,
            recurring,
            variant,
            original_line,
            related_lines,
            uom
        );
    },
});
