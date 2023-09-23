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
        this.selected_attributes = line.selected_attributes || {};
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

    updateDataFromServer(data) {
        for (const key in data) {
            let updatedValue = data[key];
            if (key === "selected_attributes") {
                updatedValue ||= {};
            }

            this[key] = updatedValue;
        }
    }

    getAttributes() {
        return this.extractProductNameAndAttributes().attributes;
    }

    extractProductNameAndAttributes() {
        const str = this.full_product_name;
        const regex = /\(([^()]+)\)[^(]*$/;
        const matches = str.match(regex);

        if (matches && matches.length > 1) {
            const attributes = matches[matches.length - 1].trim();
            const productName = str.replace(matches[0], "").trim();
            return { productName, attributes };
        }

        return { productName: str, attributes: "" };
    }
}
