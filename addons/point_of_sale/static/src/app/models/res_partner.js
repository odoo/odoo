import { registry } from "@web/core/registry";
import { normalize } from "@web/core/l10n/utils";
import { Base } from "./related_models";

export class ResPartner extends Base {
    static pythonModel = "res.partner";
    static enableLazyGetters = false;

    setup(_vals) {
        super.setup(_vals);
        this._searchString = null;
    }

    get company() {
        return this.config.company_id;
    }

    get config() {
        return this.models["pos.config"].getFirst();
    }

    get searchString() {
        if (this._searchString) {
            return this._searchString;
        }

        const fields = ["name", "barcode", "phone", "email", "vat", "parent_name", "address"];
        const raw = fields
            .map((field) => {
                if (field === "phone" && this[field]) {
                    return this[field].replace(/[+\s()-]/g, "");
                }
                return this[field] || "";
            })
            .filter(Boolean)
            .join(" ");
        this._searchString = normalize(raw);
        return this._searchString;
    }

    exactMatch(searchWord) {
        const fields = ["barcode"];
        return fields.some((field) => this[field] && normalize(this[field]) === searchWord);
    }
}
registry.category("pos_available_models").add(ResPartner.pythonModel, ResPartner);
