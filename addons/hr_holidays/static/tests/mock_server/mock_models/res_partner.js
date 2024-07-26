import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields, getKwArgs } from "@web/../tests/web_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    out_of_office_date_end = fields.Date();

    /**
     * Overrides to add out of office to employees.
     * @override
     * @type {typeof mailModels.ResPartner["prototype"]["_to_store"]}
     */
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;
        super._to_store(...arguments);
        if (!fields) {
            fields = ["out_of_office_date_end"];
        }
        for (const partner of this.browse(ids)) {
            if (fields.includes("out_of_office_date_end")) {
                store.add(this.browse(partner.id), {
                    // Not a real field but ease the testing
                    out_of_office_date_end: partner.out_of_office_date_end,
                });
            }
        }
    }
}
