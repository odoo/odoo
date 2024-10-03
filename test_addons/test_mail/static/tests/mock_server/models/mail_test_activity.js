import { models } from "@web/../tests/web_test_helpers";

export class MailTestActivity extends models.ServerModel {
    _name = "mail.test.activity";
    _inherit = ["mail.thread"];
}
