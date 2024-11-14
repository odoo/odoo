import { HrDepartment } from "@hr/../tests/mock_server/mock_models/hr_department";
import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";
import { HrEmployeePublic } from "@hr/../tests/mock_server/mock_models/hr_employee_public";
import { M2xAvatarEmployee } from "@hr/../tests/mock_server/mock_models/m2x_avatar_employee";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, mockEmojiLoading } from "@web/../tests/web_test_helpers";
import { FakeUser } from "@hr/../tests/mock_server/mock_models/fake_user";

export function defineHrModels() {
    mockEmojiLoading();
    return defineModels(hrModels);
}

export const hrModels = {
    ...mailModels,
    M2xAvatarEmployee,
    HrDepartment,
    HrEmployee,
    HrEmployeePublic,
    FakeUser,
};
