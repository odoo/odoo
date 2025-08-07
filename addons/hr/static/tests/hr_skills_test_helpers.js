import { hrModels } from "@hr/../tests/hr_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { HrEmployeeSkill } from "./mock_server/mock_models/hr_employee_skill";
import { HrSkill } from "./mock_server/mock_models/hr_skill";
import { M2oAvatarEmployee } from "./mock_server/mock_models/m2o_avatar_employee";

export function defineHrSkillModels() {
    return defineModels(hrSkillModels);
}

export const hrSkillModels = {
    ...hrModels,
    HrEmployeeSkill,
    HrSkill,
    M2oAvatarEmployee,
};
