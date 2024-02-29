/** @odoo-module */
import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ResPartner extends Base {
    static pythonModel = "res.partner";

    get searchString() {
        const fields = ['name', 'barcode', 'phone', 'mobile', 'email', 'vat', 'parent_name'];
        return fields.map((field) => {
            if ((field === 'phone' || field === 'mobile') && this[field]) {
                return this[field].split(" ").join("");
            }
            return this[field] || "";
        }).filter(Boolean).join(" ");
    }
}
registry.category("pos_available_models").add(ResPartner.pythonModel, ResPartner);
