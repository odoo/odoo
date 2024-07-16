import { makeKwArgs, models } from "@web/../tests/web_test_helpers";

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
            const [data] = this.read(
                follower.id,
                ["display_name", "email", "is_active", "name", "partner_id"],
                makeKwArgs({ load: false })
            );
            data.partner = { id: follower.partner_id, type: "partner" };
            data.thread = { id: follower.res_id, model: follower.res_model };
            store.add("mail.followers", data);
        }
    }
}
