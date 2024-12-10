import { mailModels } from "@mail/../tests/mail_test_helpers";

export class MailActivity extends mailModels.MailActivity {
    /** @param {number[]} ids */
    _to_store(ids, store) {
        super._to_store(...arguments);
        for (const activity of this.browse(ids)) {
            if (activity.request_partner_id) {
                store.add(this.browse(activity.id), {
                    request_partner_id: activity.request_partner_id
                });
            }
        }
    }
}
