import { fields, models } from "@web/../tests/web_test_helpers";

export class MailRole extends models.ServerModel {
    _name = "mail.role";

    name = fields.Char();
}
