import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { Command, fields, getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class LivechatChannel extends models.ServerModel {
    _name = "im_livechat.channel";

    available_operator_ids = fields.Many2many({ relation: "res.users" }); // FIXME: somehow not fetched properly
    user_ids = fields.Many2many({ relation: "res.users" }); // FIXME: somehow not fetched properly

    /** @param {integer} id */
    action_join(id) {
        this.write([id], { user_ids: [Command.link(this.env.user.id)] });
        const [partner] = this.env["res.partner"].read(this.env.user.partner_id);
        this.env["bus.bus"]._sendone(
            partner,
            "mail.record/insert",
            new mailDataHelpers.Store(
                this.browse(id),
                makeKwArgs({ fields: ["are_you_inside", "name"] })
            ).get_result()
        );
    }

    /** @param {integer} id */
    action_quit(id) {
        this.write(id, { user_ids: [Command.unlink(this.env.user.id)] });
        const [partner] = this.env["res.partner"].read(this.env.user.partner_id);
        this.env["bus.bus"]._sendone(
            partner,
            "mail.record/insert",
            new mailDataHelpers.Store(
                this.browse(id),
                makeKwArgs({ fields: ["are_you_inside", "name"] })
            ).get_result()
        );
    }

    /** @param {integer} id */
    _compute_available_operator_ids(id) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const [livechatChannel] = this.browse(id);
        const users = ResUsers.browse(livechatChannel.user_ids);
        return users.filter((user) => user.im_status === "online");
    }
    /** @param {integer} id */
    _get_livechat_discuss_channel_vals(id, operator_info) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        const agent = operator_info['agent']

        const membersToAdd = [
            Command.create({
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                partner_id: agent.partner_id,
            }),
        ];
        const guest = ResUsers._is_public(this.env.uid) && MailGuest._get_guest_from_context();
        if (guest) {
            membersToAdd.push(Command.create({ guest_id: guest.id }));
        }
        let visitorUser;
        if (this.env.user && !ResUsers._is_public(this.env.uid) && this.env.user !== agent) {
            visitorUser = this.env.user;
            membersToAdd.push(
                Command.create({
                    livechat_member_type: "visitor",
                    partner_id: visitorUser.partner_id,
                })
            );
        }
        const membersName = [
            visitorUser ? visitorUser.display_name : guest.name,
            agent.livechat_username ? agent.livechat_username : agent.name,
        ];
        return {
            channel_partner_ids: [agent.partner_id],
            channel_member_ids: membersToAdd,
            livechat_operator_id: agent.partner_id,
            livechat_channel_id: id,
            livechat_status: "in_progress",
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

    _to_store(store, fields) {
        const kwargs = getKwArgs(arguments, "store", "fields");
        fields = kwargs.fields;
        store._add_record_fields(
            this,
            fields.filter((field) => field !== "are_you_inside")
        );
        for (const livechatChannel of this) {
            if (fields.includes("are_you_inside")) {
                store._add_record_fields(this.browse(livechatChannel.id), {
                    are_you_inside: livechatChannel.user_ids.includes(this.env.user.id),
                });
            }
        }
    }
}
