import { Store } from "@mail/../tests/mock_server/store";

import { getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class DiscussChannelRtcSession extends models.ServerModel {
    _name = "discuss.channel.rtc.session";

    create() {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const sessionIds = super.create(...arguments);
        const rtcSessions = this.browse(sessionIds);
        /** @type {Record<string, DiscussChannelRtcSession>} */
        const sessionsByChannelId = {};
        for (const session of rtcSessions) {
            const [member] = DiscussChannelMember.browse(session.channel_member_id);
            if (!sessionsByChannelId[member.channel_id]) {
                sessionsByChannelId[member.channel_id] = [];
            }
            sessionsByChannelId[member.channel_id].push(session);
        }
        const notifications = [];
        for (const [channelId, sessions] of Object.entries(sessionsByChannelId)) {
            const [channel] = DiscussChannel.search_read([["id", "=", Number(channelId)]]);
            notifications.push([
                channel,
                "mail.record/insert",
                new Store()
                    .add(DiscussChannel.browse(channel.id), (res) =>
                        res.many("rtc_session_ids", "_store_rtc_session_fields", {
                            mode: "ADD",
                            value: this.browse(sessions.map((session) => session.id)),
                        })
                    )
                    .as_dict(),
            ]);
        }
        for (const record of rtcSessions) {
            const [channel] = DiscussChannel.browse(record.channel_id);
            if (channel.rtc_session_ids.length === 1) {
                DiscussChannel.message_post(
                    channel.id,
                    makeKwArgs({
                        body: `<div data-oe-type="call" class="o_mail_notification"></div>`,
                        message_type: "notification",
                        subtype_xmlid: "mail.mt_comment",
                    })
                );
            }
        }
        BusBus._sendmany(notifications);
        return sessionIds;
    }

    unlink(ids) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        const sessions = this.browse(ids);
        for (const session of sessions) {
            const [partner] = ResPartner.search_read([["id", "=", session.partner_id]]);
            BusBus._sendmany([
                [
                    partner,
                    "discuss.channel.rtc.session/ended",
                    {
                        sessionId: session.id,
                    },
                ],
                [
                    partner,
                    "mail.record/insert",
                    new Store()
                        .add(DiscussChannel.browse(Number(session.channel_id)), (res) =>
                            res.many("rtc_session_ids", [], { mode: "DELETE", value: sessions })
                        )
                        .as_dict(),
                ],
            ]);
        }
        super.unlink(...arguments);
    }

    _store_rtc_session_fields(res) {
        res.one("channel_member_id", "_store_avatar_card_fields");
    }

    _store_extra_fields(res) {
        this._store_rtc_session_fields(res);
        res.extend(["is_camera_on", "is_deaf", "is_muted", "is_screen_sharing_on"]);
    }

    /**
     * @param {number} id
     * @param {object} values
     */
    _update_and_broadcast(id, values) {
        const kwargs = getKwArgs(arguments, "id", "values");
        id = kwargs.id;
        delete kwargs.id;
        values = kwargs.values;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").DiscussChannelRtcSession} */
        const DiscussChannelRtcSession = this.env["discuss.channel.rtc.session"];

        this.write([id], values);
        const [session] = DiscussChannelRtcSession.browse(id);
        const [member] = DiscussChannelMember.browse(session.channel_member_id);
        const [channel] = DiscussChannel.search_read([["id", "=", member.channel_id]]);
        BusBus._sendone(channel, "discuss.channel.rtc.session/update_and_broadcast", {
            store_data: new Store()
                .add(DiscussChannelRtcSession.browse(id), "_store_extra_fields")
                .as_dict(),
            channelId: channel.id,
        });
    }
}
