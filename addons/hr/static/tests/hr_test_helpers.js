import { HrDepartment } from "./mock_server/mock_models/hr_department";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { busModels } from "@bus/../tests/bus_test_helpers";
import { defineModels, webModels } from "@web/../tests/web_test_helpers";

export const hrModels = {
    HrDepartment,
    ResUsers,
};

export function defineHrModels() {
    return defineModels({ ...webModels, ...busModels, ...mailModels, ...hrModels });
}
