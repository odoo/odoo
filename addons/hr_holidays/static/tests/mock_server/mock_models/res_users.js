import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields, getKwArgs } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    employee_id = fields.Many2one({ relation: "hr.employee" });
    employee_ids = fields.One2many({
        relation: "hr.employee",
        inverse: "user_id",
    });
    leave_date_to = fields.Date({ related: false });

    _get_store_avatar_card_related_fields() {
        return {
            employee_ids: ["leave_date_to"],
        };
    }
    _get_store_avatar_card_fields() {
        const fields = super._get_store_avatar_card_fields();
        return fields.concat(["employee_ids"]);
    }

    /**
     * @param {number[]} ids
     * @returns {Record<string, ModelRecord>}
     */
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "id", "store", "fields");
        super._to_store(...arguments);
        fields = kwargs.fields;
        if (!fields.includes("employee_ids")) {
            for (const user of this.browse(ids)) {
                const [data] = this._read_format(user.id, ["employee_ids"], false);
                const employees = this.env["hr.employee"].browse(data.employee_ids);
                for (const employee of employees) {
                    const [data_employee] = this.env["hr.employee"]._read_format(
                        employee.id,
                        ["leave_date_to"],
                        false
                    );
                    store.add(this.env["hr.employee"].browse(employee.id), data_employee);
                }
            }
        }
    }
}
