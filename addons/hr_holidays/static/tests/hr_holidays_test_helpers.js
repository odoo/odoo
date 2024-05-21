import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { HrEmployee } from "./mock_server/mock_models/hr_employee";

export function defineHrHolidaysModels() {
    return defineModels(hrHolidaysModels);
}

export const hrHolidaysModels = { ...mailModels, ResPartner, HrEmployee };
