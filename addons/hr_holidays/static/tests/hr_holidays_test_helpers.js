import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { HrEmployee } from "./mock_server/mock_models/hr_employee";
import { HrLeave } from "./mock_server/mock_models/hr_leave";
import { HrDepartment } from "./mock_server/mock_models/hr_department";
import { HrLeaveType } from "./mock_server/mock_models/hr_leave_type";

export function defineHrHolidaysModels() {
    return defineModels(hrHolidaysModels);
}

export const hrHolidaysModels = {
    ...mailModels,
    ResPartner,
    HrEmployee,
    HrDepartment,
    HrLeaveType,
    HrLeave,
};
