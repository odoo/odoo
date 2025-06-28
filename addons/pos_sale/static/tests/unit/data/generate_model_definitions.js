import { patch } from "@web/core/utils/patch";
import {
    modelsToLoad,
    posModels,
    PosOrderLine,
    ProductTemplate,
    ResPartner,
} from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { defineModels, models } from "@web/../tests/web_test_helpers";

export class SaleOrder extends models.ServerModel {
    _name = "sale.order";

    _load_pos_data_fields() {
        return [
            "name",
            "state",
            "user_id",
            "order_line",
            "partner_id",
            "pricelist_id",
            "fiscal_position_id",
            "amount_total",
            "amount_untaxed",
            "amount_unpaid",
            "picking_ids",
            "partner_shipping_id",
            "partner_invoice_id",
            "date_order",
            "write_date",
        ];
    }
}

export class SaleOrderLine extends models.ServerModel {
    _name = "sale.order.line";

    _load_pos_data_fields() {
        return [
            "discount",
            "display_name",
            "price_total",
            "price_unit",
            "product_id",
            "product_uom_qty",
            "qty_delivered",
            "qty_invoiced",
            "qty_to_invoice",
            "display_type",
            "name",
            "tax_ids",
            "is_downpayment",
            "extra_tax_data",
            "write_date",
            "is_repair_line",
        ];
    }
}

patch(PosOrderLine.prototype, {
    _load_pos_data_fields() {
        return [
            ...super._load_pos_data_fields(),
            "sale_order_origin_id",
            "sale_order_line_id",
            "down_payment_details",
            "settled_order_id",
            "settled_invoice_id",
        ];
    },
});

patch(ProductTemplate.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "sale_line_warn_msg", "invoice_policy"];
    },
});

patch(ResPartner.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "sale_warn_msg"];
    },
});

patch(modelsToLoad, [...modelsToLoad, "sale.order", "sale.order.line"]);
patch(posModels, [...posModels, SaleOrder, SaleOrderLine]);
defineModels([SaleOrder, SaleOrderLine]);
