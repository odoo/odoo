import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ResPartner extends Base {
    static pythonModel = "res.partner";

    get searchString() {
        const fields = [
            "name",
            "barcode",
            "phone",
            "mobile",
            "email",
            "vat",
            "parent_name",
            "contact_address",
        ];
        return fields
            .map((field) => {
                if ((field === "phone" || field === "mobile") && this[field]) {
                    return this[field].replace(/[+\s()-]/g, "");
                }
                return this[field] || "";
            })
            .filter(Boolean)
            .join(" ");
    }

    exactMatch(searchWord) {
        const fields = ["barcode"];
        return fields.some((field) => this[field] && this[field].toLowerCase() === searchWord);
    }
}
registry.category("pos_available_models").add(ResPartner.pythonModel, ResPartner);
