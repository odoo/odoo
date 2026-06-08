/* global Sha1 */

import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    _load_pos_data_fields() {
        return ["name", "user_id", "work_contact_id"];
    }

    _records = [
        {
            id: 2,
            name: "Administrator",
            user_id: 2,
            work_contact_id: 3,
        },
        {
            id: 3,
            name: "Employee1",
            user_id: 3,
            work_contact_id: 3,
        },
        {
            id: 4,
            name: "A Little Guy",
        },
    ];

    _load_pos_data_read(records) {
        const employeeRoles = {
            2: "manager",
            3: "cashier",
            4: "minimal",
        };
        records.forEach((emp) => {
            emp._role = employeeRoles[emp.id] || "manager";
            if (emp.id === 2) {
                emp._pin = Sha1.hash("1234");
            }
        });
        return records;
    }
}
patch(hootPosModels, [...hootPosModels, HrEmployee]);
