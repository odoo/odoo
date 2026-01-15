import { defineModels } from "@web/../tests/web_test_helpers";
import { ResUsers } from "@hr_holidays/../tests/mock_server/mock_models/res_users";
import { ResPartner } from "@hr_holidays/../tests/mock_server/mock_models/res_partner";
import { HrEmployee } from "@hr_holidays/../tests/mock_server/mock_models/hr_employee";
import { HrLeave } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave";
import { HrDepartment } from "@hr_holidays/../tests/mock_server/mock_models/hr_department";
import { HrLeaveType } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave_type";
import { hrModels } from "@hr/../tests/hr_test_helpers";

export function defineHrHolidaysModels() {
    return defineModels(hrHolidaysModels);
}

export const hrHolidaysModels = {
    ...hrModels,
    ResUsers,
    ResPartner,
    HrEmployee,
    HrDepartment,
    HrLeaveType,
    HrLeave,
};
