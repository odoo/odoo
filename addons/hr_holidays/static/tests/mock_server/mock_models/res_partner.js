import { hrModels } from "@hr/../tests/hr_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResPartner extends hrModels.ResPartner {
    leave_date_to = fields.Date({ related: false });
}
