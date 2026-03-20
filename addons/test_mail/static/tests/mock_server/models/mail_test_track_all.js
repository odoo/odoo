import { fields, models } from "@web/../tests/web_test_helpers";

export class MailTestTrackAll extends models.ServerModel {
    _name = "mail.test.track.all";
    _inherit = ["mail.thread"];

    float_field_with_digits = fields.Float({
        digits: [10, 8],
    });
}
