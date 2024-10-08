import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ResPartner extends Base {
    static pythonModel = "res.partner";

    exactMatch(searchWord) {
        const fields = ["barcode"];
        return fields.some((field) => this[field] && this[field] === searchWord);
    }

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
                    return this[field].split(" ").join("");
                }
                return this[field] || "";
            })
            .filter(Boolean)
            .join(" ");
    }

    get customListFields() {
        return { list: ["name", "phone", "email", "vat"], search: [] };
    }

    get customListSearches() {
        return {
            name: (obj) => obj.name || "",
            phone: (obj) => obj.phone || "",
            email: (obj) => obj.email || "",
            vat: (obj) => obj.vat || "",
        };
    }
}
registry.category("pos_available_models").add(ResPartner.pythonModel, ResPartner);
