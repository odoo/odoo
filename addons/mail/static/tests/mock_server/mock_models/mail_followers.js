import { models } from "@web/../tests/web_test_helpers";

export class MailFollowers extends models.ServerModel {
    _name = "mail.followers";

    _to_store(ids, store) {
        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const followers = MailFollowers._filter([["id", "in", ids]]);
        // sorted from lowest ID to highest ID (i.e. from least to most recent)
        followers.sort((f1, f2) => (f1.id < f2.id ? -1 : 1));
        store.add(ResPartner.browse(followers.map((follower) => follower.partner_id)));
        for (const follower of followers) {
            store.add("Follower", {
                display_name: follower.display_name,
                email: follower.email,
                id: follower.id,
                is_active: follower.is_active,
                name: follower.name,
                partner_id: follower.partner_id,
                partner: { id: follower.partner_id, type: "partner" },
                thread: { id: follower.res_id, model: follower.res_model },
            });
        }
    }
}
