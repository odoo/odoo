import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";
import { HrEmployeePublic } from "@hr/../tests/mock_server/mock_models/hr_employee_public";
import { mailModels } from "@mail/../tests/mail_test_helpers";

export const hrModels = { ...mailModels, HrEmployee, HrEmployeePublic };
