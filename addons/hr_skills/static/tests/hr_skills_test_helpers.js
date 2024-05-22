import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { HrEmployee } from "./mock_server/mock_models/hr_employee";
import { HrEmployeeSkill } from "./mock_server/mock_models/hr_employee_skill";
import { HrSkill } from "./mock_server/mock_models/hr_skill";
import { M2oAvatarEmployee } from "./mock_server/mock_models/m2o_avatar_employee";
import { HrEmployeePublic } from "./mock_server/mock_models/hr_employee_public";

export function defineHrSkillModels() {
    return defineModels(hrSkillModels);
}

export const hrSkillModels = {
    ...mailModels,
    HrEmployee,
    HrEmployeeSkill,
    HrEmployeePublic,
    HrSkill,
    M2oAvatarEmployee,
};
