import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    module_pos_hr: true,
    manager_employee_ids: [2],
    cashier_employee_ids: [3],
    restrictive_employee_ids: [4],
    supervised_employee_ids: [5],
}));
