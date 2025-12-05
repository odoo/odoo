import { Record, fields } from "@mail/model/export";

export class HrEmployeePublic extends Record {
    static _name = "hr.employee.public";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {number} */
    company_id = fields.One("res.company");
    department_id = fields.One("hr.department");
    /** @type {string} */
    job_title;
    user_id = fields.One("res.users");
    work_contact_id = fields.One("res.partner");
    /** @type {string} */
    work_email;
    work_location_id = fields.One("hr.work.location");
    /** @type {string} */
    work_phone;
}

HrEmployeePublic.register();
