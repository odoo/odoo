/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";
import { uuidv4 } from "@point_of_sale/utils";

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
        selected_attributes,
        combo_parent_uuid,
        combo_id,
        child_lines,
    }) {
        super();
        this.setup(...arguments);
    }

    setup(line) {
        // server data
        this.id = line.id || null;
        this.uuid = line.uuid || uuidv4();
        this.full_product_name = line.full_product_name;
        this.product_id = line.product_id;
        this.qty = line.qty ? line.qty : 0;
        this.customer_note = line.customer_note;
        this.price_unit = line.price_unit || 0;
        this.price_subtotal_incl = line.price_subtotal_incl || 0;
        this.price_subtotal = line.price_subtotal || 0;
        this.selected_attributes = line.selected_attributes || [];
        this.combo_parent_uuid = line.combo_parent_uuid || null;
        this.combo_id = line.combo_id || null;
        this.child_lines = line.child_lines || [];
    }

    isChange(lastChange) {
        for (const key in lastChange) {
            if (JSON.stringify(lastChange[key]) !== JSON.stringify(this[key])) {
                return true;
            }
        }

        return false;
    }

    get displayPrice() {
        // for the moment we use price with tax included but we should look at the config setup
        return this.price_subtotal_incl;
    }

    getProductName(productsByIds) {
        const product = productsByIds[this.product_id];

        if (product.attributes.length === 0) {
            this.full_product_name = product.name;
            return this.full_product_name;
        }

        const productAttributeValues = product.attributes
            .map((a) => {
                for (const value of a.values) {
                    value.sequence = a.sequence;
                }
                return a.values;
            })
            .flat();

        const selectedAttributeString = this.selected_attributes
            .map((attributeValId) => productAttributeValues.find((a) => a.id == attributeValId))
            .sort((a, b) => a.sequence - b.sequence)
            .map((a) => a.name)
            .join(", ");

        this.full_product_name = `${product.name} (${selectedAttributeString})`;
        return this.full_product_name;
    }

    updateDataFromServer(data) {
        for (const key in data) {
            let updatedValue = data[key];
            if (key === "selected_attributes") {
                updatedValue ||= {};
            }

            this[key] = updatedValue;
        }
    }
}
