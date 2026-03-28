import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ResPartner extends Base {
    static pythonModel = "res.partner";
    static enableLazyGetters = false;

    setup(_vals) {
        super.setup(_vals);
        this._searchString = null;
    }

    get searchString() {
        if (this._searchString) {
            return this._searchString;
        }

        const fields = [
            "name",
            "barcode",
            "phone",
            "email",
            "vat",
            "parent_name",
            "pos_contact_address",
        ];
        this._searchString = fields
            .map((field) => {
                if (field === "phone" && this[field]) {
                    return this[field].replace(/[+\s()-]/g, "");
                }
                return this[field] || "";
            })
            .filter(Boolean)
            .join(" ");
        return this._searchString;
    }

    exactMatch(searchWord) {
        const fields = ["barcode"];
        return fields.some((field) => this[field] && this[field].toLowerCase() === searchWord);
    }
}
registry.category("pos_available_models").add(ResPartner.pythonModel, ResPartner);
