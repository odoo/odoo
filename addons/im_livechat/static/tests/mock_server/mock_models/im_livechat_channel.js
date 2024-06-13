import { Command, fields, models } from "@web/../tests/web_test_helpers";

export class LivechatChannel extends models.ServerModel {
    _name = "im_livechat.channel";

    available_operator_ids = fields.Many2many({ relation: "res.users" }); // FIXME: somehow not fetched properly
    user_ids = fields.Many2many({ relation: "res.users" }); // FIXME: somehow not fetched properly

    /** @param {integer} id */
    action_join(id) {
        this.write([id], { user_ids: [Command.link(this.env.user.id)] });
        const self = this.read([id])[0];
        const [partner] = this.env["res.partner"].read(this.env.user.partner_id);
        this.env["bus.bus"]._sendone(partner, "mail.record/insert", {
            LivechatChannel: { id, name: self.name, hasSelfAsMember: true },
        });
    }

    /** @param {integer} id */
    action_quit(id) {
        this.write(id, { user_ids: [Command.unlink(this.env.user.id)] });
        const [partner] = this.env["res.partner"].read(this.env.user.partner_id);
        const self = this.read([id])[0];
        this.env["bus.bus"]._sendone(partner, "mail.record/insert", {
            LivechatChannel: { id, name: self.name, hasSelfAsMember: false },
        });
    }

    /** @param {integer} id */
    _compute_available_operator_ids(id) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const livechatChannel = this._filter([["id", "=", id]])[0];
        const users = ResUsers._filter([["id", "in", livechatChannel.user_ids]]);
        return users.filter((user) => user.im_status === "online");
    }
    /** @param {integer} id */
    _get_livechat_discuss_channel_vals(id, anonymous_name, previous_operator_id, country_id) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const operator = this._get_operator(id, previous_operator_id);
        if (!operator) {
            return false;
        }
        // partner to add to the discuss.channel
        const membersToAdd = [
            Command.create({
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: operator.partner_id,
            }),
        ];
        const membersName = [
            this.env.user ? this.env.user.display_name : anonymous_name,
            operator.livechat_username ? operator.livechat_username : operator.name,
        ];
        return {
            channel_partner_ids: [operator.partner_id],
            channel_member_ids: membersToAdd,
            livechat_active: true,
            livechat_operator_id: operator.partner_id,
            livechat_channel_id: id,
            anonymous_name: ResUsers._is_public(this.env.uid) ? false : anonymous_name,
            country_id: country_id,
            channel_type: "livechat",
            name: membersName.join(" "),
        };
    }
    /**
     * Simplified mock implementation: returns
     * the previous operator if he is still available
     * or the first available operator.
     *
     * @param {integer} id
     */
    _get_operator(id, previous_operator_id) {
        const availableUsers = this._compute_available_operator_ids(id);
        return (
            availableUsers.find((operator) => operator.partner_id === previous_operator_id) ??
            availableUsers[0]
        );
    }
}
