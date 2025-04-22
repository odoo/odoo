import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    leave_date_to = fields.Date({ related: false });
}
