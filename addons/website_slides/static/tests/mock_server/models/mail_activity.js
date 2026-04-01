import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { makeKwArgs } from "@web/../tests/web_test_helpers";

export class MailActivity extends mailModels.MailActivity {
    /** @param {number[]} ids */
    _to_store(store) {
        super._to_store(...arguments);
        for (const activity of this) {
            if (activity.request_partner_id) {
                store._add_record_fields(this.browse(activity.id), {
                    request_partner_id: mailDataHelpers.Store.one(
                        this.env["res.partner"].browse(activity.request_partner_id),
                        makeKwArgs({ only_id: true })
                    ),
                });
            }
        }
    }
}
