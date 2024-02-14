import { models } from "@web/../tests/web_test_helpers";

export class MailFollowers extends models.ServerModel {
    _name = "mail.followers";

    _format_for_chatter(ids) {
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const followers = MailFollowers._filter([["id", "in", ids]]);
        // sorted from lowest ID to highest ID (i.e. from least to most recent)
        followers.sort((f1, f2) => (f1.id < f2.id ? -1 : 1));
        const partnerFormats = ResPartner.mail_partner_format(
            followers.map((follower) => follower.partner_id)
        );
        return followers.map((follower) => {
            return {
                id: follower.id,
                partner_id: follower.partner_id,
                name: follower.name,
                display_name: follower.display_name,
                email: follower.email,
                is_active: follower.is_active,
                partner: partnerFormats[follower.partner_id],
            };
        });
    }
}
