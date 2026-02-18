import { hrModels } from "@hr/../tests/hr_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResUsers extends hrModels.ResUsers {
    leave_date_to = fields.Date({ related: false });
    leave_date_from = fields.Date({ related: false });
    request_date_from_period = fields.Selection({
        selection: [
            ["am", "Morning"],
            ["pm", "Afternoon"],
        ],
    });
}
