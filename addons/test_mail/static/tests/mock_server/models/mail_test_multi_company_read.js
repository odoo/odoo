import { models } from "@web/../tests/web_test_helpers";

export class MailTestMultiCompanyRead extends models.ServerModel {
    _name = "mail.test.multi.company.read";
    _inherit = ["mail.thread"];
    _mail_post_access = "read";
}
