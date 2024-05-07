import { models } from "@web/../tests/web_test_helpers";

export class MailTestTrackAll extends models.ServerModel {
    _name = "mail.test.track.all";
    _inherit = ["mail.thread"];
}
