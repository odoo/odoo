import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    out_of_office_date_end = fields.Date();

    /**
     * Overrides to add out of office to employees.
     * @override
     * @type {typeof mailModels.ResPartner["prototype"]["_to_store"]}
     */
    _to_store(ids, store) {
        super._to_store(...arguments);
        const partners = this._filter([["id", "in", ids]], {
            active_test: false,
        });
        for (const partner of partners) {
            store.add("Persona", {
                id: partner.id,
                // Not a real field but ease the testing
                out_of_office_date_end: partner.out_of_office_date_end,
                type: "partner",
            });
        }
    }
}
