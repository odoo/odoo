import { HrDepartment } from "@hr/../tests/mock_server/mock_models/hr_department";
import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";
import { HrEmployeePublic } from "@hr/../tests/mock_server/mock_models/hr_employee_public";
import { M2xAvatarEmployee } from "@hr/../tests/mock_server/mock_models/m2x_avatar_employee";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { FakeUser } from "@hr/../tests/mock_server/mock_models/fake_user";
import { HrVersion } from "./mock_server/mock_models/hr_version";
import { HrJob } from "./mock_server/mock_models/hr_job";
import { HrWorkLocation } from "./mock_server/mock_models/hr_work_location";
import { ResourceResource } from "@resource/../tests/mock_server/mock_models/resource_resource";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { ResPartner } from "./mock_server/mock_models/res_partner";

export function defineHrModels() {
    return defineModels(hrModels);
}

export const hrModels = {
    ...mailModels,
    M2xAvatarEmployee,
    HrDepartment,
    HrEmployee,
    HrVersion,
    HrEmployeePublic,
    FakeUser,
    HrJob,
    HrWorkLocation,
    ResourceResource,
    ResUsers,
    ResPartner,
};
