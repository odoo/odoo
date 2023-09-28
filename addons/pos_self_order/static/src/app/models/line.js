/** @odoo-module **/
import { BaseOrderline } from "@point_of_sale/app/base_models/base_orderline";
export class Line extends BaseOrderline {
    isChange(lastChange) {
        for (const key in lastChange) {
            if (JSON.stringify(lastChange[key]) !== JSON.stringify(this[key])) {
                return true;
            }
        }

        return false;
    }

    get attributes() {
        return Object.entries(this.selected_attributes).map(([key, value]) => {
            return { name: key, value };
        });
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
