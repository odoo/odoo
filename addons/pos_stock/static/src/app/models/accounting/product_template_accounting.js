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
        related_lines = []
    ) {
        if (original_line && original_line.isLotTracked() && variant) {
            related_lines.push(
                ...original_line.order_id.lines.filter((line) => line.product_id.id == variant.id)
            );
            quantity = related_lines.reduce((sum, line) => sum + line.getQuantity(), 0);
        }
        return super.getPrice(
            pricelist,
            quantity,
            price_extra,
            recurring,
            variant,
            original_line,
            related_lines
        );
    },
});
