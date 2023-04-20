/** @odoo-module **/
import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";

export class ProductQuantityField extends FloatField {}
ProductQuantityField.template = "mrp.ProductQuantityField"

registry.category('fields').add('product_qty', ProductQuantityField);
