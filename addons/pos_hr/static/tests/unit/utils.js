import { HrEmployee } from "./data/hr_employee.data";
import { patch } from "@web/core/utils/patch";

export function removeAllEmployeePin() {
    patch(HrEmployee.prototype, {
        _load_pos_data_read(records) {
            const employees = super._load_pos_data_read(records);
            employees.forEach((employee) => (employee._pin = undefined));
            return employees;
        },
    });
}
