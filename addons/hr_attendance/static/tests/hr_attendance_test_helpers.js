import { hrModels } from "@hr/../tests/hr_test_helpers";

import { defineModels } from "@web/../tests/web_test_helpers";

export const hrAttendanceModels = { ...hrModels };

export function defineHrAttendanceModels() {
    return defineModels(hrAttendanceModels);
}
