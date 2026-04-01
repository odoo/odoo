import { Record, fields } from "@mail/core/common/record";

export class HrEmployee extends Record {
    static _name = "hr.employee";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {number} */
    company_id = fields.One("res.company");
    department_id = fields.One("hr.department");
    /** @type {string} */
    job_title;
    work_contact_id = fields.One("res.partner");
    user_id = fields.One("res.users");
    /** @type {string} */
    work_email;
    work_location_id = fields.One("hr.work.location");
    /** @type {string} */
    work_phone;
}

HrEmployee.register();
