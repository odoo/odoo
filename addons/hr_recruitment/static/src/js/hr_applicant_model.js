import { fields, Record } from "@mail/core/common/record";

export class HrApplicant extends Record {
    static _name = "hr.applicant";
    static id = "id";

    partner_id = fields.One("res.partner", { inverse: "applicant_ids" });
    /**
     * The actual name of the partner (partner_id.name contains the email).
     *
     * @type {string}
     */
    partner_name;
}

HrApplicant.register();
