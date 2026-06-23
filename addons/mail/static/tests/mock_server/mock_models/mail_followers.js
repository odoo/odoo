import { models } from "@web/../tests/web_test_helpers";

export class MailFollowers extends models.ServerModel {
    _name = "mail.followers";

    _compute_display_name() {
        for (const record of this) {
            const [partner] = this.env["res.partner"].browse(record.partner_id);
            record.display_name = partner.display_name;
        }
    }

    _store_follower_fields(res) {
        res.extend(["display_name", "email", "is_active", "name"]);
        res.one("partner_id", "_store_partner_fields", { sudo: true });
        res.one("thread", [], { as_thread: true });
    }
}
