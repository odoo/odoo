import { HrDepartment } from "./mock_server/mock_models/hr_department";
import { HrEmployee } from "./mock_server/mock_models/hr_employee";
import { HrEmployeePublic } from "./mock_server/mock_models/hr_employee_public";
import { M2XAVatarEmployee } from "./mock_server/mock_models/m2x_avatar_employee";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { busModels } from "@bus/../tests/bus_test_helpers";
import { defineModels, webModels } from "@web/../tests/web_test_helpers";

export const hrModels = {
    HrDepartment,
    HrEmployee,
    HrEmployeePublic,
    M2XAVatarEmployee,
    ResUsers,
};

export function defineHrModels() {
    return defineModels({ ...webModels, ...busModels, ...mailModels, ...hrModels });
}
