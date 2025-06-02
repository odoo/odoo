import { models } from "@web/../tests/web_test_helpers";

export class MailTestMultiCompanyWithActivityRead extends models.ServerModel {
    _name = "mail.test.multi.company.with.activity.read";
    _mail_post_access = "read";
}
