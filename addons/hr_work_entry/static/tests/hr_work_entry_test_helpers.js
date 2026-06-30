import { defineModels } from "@web/../tests/web_test_helpers";
import { hrModels } from "@hr/../tests/hr_test_helpers";
import { HrEmployee } from "@hr_work_entry/../tests/mock_server/mock_models/hr_employee";
import { HrWorkEntryType } from "@hr_work_entry/../tests/mock_server/mock_models/hr_work_entry_type";
import { HrWorkEntry } from "@hr_work_entry/../tests/mock_server/mock_models/hr_work_entry";

export function defineHrWorkEntryModels() {
    return defineModels(hrWorkEntryModels);
}

export const hrWorkEntryModels = {
    ...hrModels,
    HrEmployee,
    HrWorkEntry,
    HrWorkEntryType,
};
