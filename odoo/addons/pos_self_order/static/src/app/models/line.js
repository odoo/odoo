/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";
import { uuidv4 } from "@point_of_sale/utils";
import { ProductCustomAttribute } from "@point_of_sale/app/store/models/product_custom_attribute";

export class Line extends Reactive {
    constructor({
        id,
        uuid,
        product_id,
        qty,
        customer_note,
        full_product_name,
        price_unit,
        price_subtotal_incl,
        price_subtotal,
        attribute_value_ids,
        custom_attribute_value_ids,
        combo_parent_uuid,
        combo_id,
        combo_line_id,
        child_lines,
    }) {
        super();
        this.setup(...arguments);
    }

    setup(line) {
        // server data
        this.id = line.id || null;
        this.uuid = line.uuid || uuidv4();
        this.full_product_name = line.full_product_name || "";
        this.product_id = line.product_id;
        this.qty = line.qty ? line.qty : 0;
        this.customer_note = line.customer_note || "";
        this.price_unit = line.price_unit || 0;
        this.price_subtotal_incl = line.price_subtotal_incl || 0;
        this.price_subtotal = line.price_subtotal || 0;
        this.attribute_value_ids = line.attribute_value_ids || [];
        this.custom_attribute_value_ids = line.custom_attribute_value_ids || [];
        this.combo_parent_uuid = line.combo_parent_uuid || null;
        this.combo_id = line.combo_id || null;
        this.combo_line_id = line.combo_line_id || null;
        this.child_lines = line.child_lines || [];

        this.initCustomAttribute();
    }
    initCustomAttribute() {
        this.custom_attribute_value_ids = this.custom_attribute_value_ids.map(
            (customAttribute) => new ProductCustomAttribute(customAttribute)
        );
    }

    isChange(lastChange) {
        for (const key in lastChange) {
            if (JSON.stringify(lastChange[key]) !== JSON.stringify(this[key])) {
                return true;
            }
        }

        return false;
    }

    get attributes() {
        return Object.entries(this.attribute_value_ids).map(([key, value]) => {
            return { name: key, value };
        });
    }

    updateDataFromServer(data) {
        for (const key in data) {
            let updatedValue = data[key];
            if (key === "attribute_value_ids") {
                updatedValue ||= {};
            }

            this[key] = updatedValue;
        }
    }
}
