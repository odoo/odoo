import { fields, models } from "@web/../tests/web_test_helpers";


export class SaleOrderLine extends models.ServerModel {
    _name = "sale.order.line";

    // Store the field for testing to be able to set the translation at the record creation.
    translated_product_name = fields.Char({store: true});
}
