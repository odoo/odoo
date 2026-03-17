import { defineModels } from "@web/../tests/web_test_helpers";
import { ResUsers } from "@hr_time/../tests/mock_server/mock_models/res_users";
import { ResPartner } from "@hr_time/../tests/mock_server/mock_models/res_partner";
import { HrEmployee } from "@hr_time/../tests/mock_server/mock_models/hr_employee";
import { HrTime } from "@hr_time/../tests/mock_server/mock_models/hr_time";
import { HrDepartment } from "@hr_time/../tests/mock_server/mock_models/hr_department";
import { HrWorkEntryType } from "@hr_time/../tests/mock_server/mock_models/hr_work_entry_type";
import { hrModels } from "@hr/../tests/hr_test_helpers";

export function defineHrTimeModels() {
    return defineModels(hrHolidaysModels);
}

export const hrHolidaysModels = {
    ...hrModels,
    ResUsers,
    ResPartner,
    HrEmployee,
    HrDepartment,
    HrWorkEntryType,
    HrTime,
};
