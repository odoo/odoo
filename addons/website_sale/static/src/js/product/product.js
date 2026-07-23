import { productProps } from '@sale/js/product/product';
import { t } from "@odoo/owl";

Object.assign(productProps, {
    strikethrough_price: t.number().optional(),
    base_unit_price: t.number().optional(),
    can_be_sold: t.boolean().optional(),
    // The following fields are needed for tracking.
    category_name: t.string().optional(),
    currency_name: t.string().optional(),
});
