import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

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
                new mailDataHelpers.Store(DiscussChannel.browse(channel.id), {
                    rtcSessions: mailDataHelpers.Store.many(
                        this.browse(sessions.map((session) => session.id)),
                        "ADD"
                    ),
                }).get_result(),
            ]);
        }
        BusBus._sendmany(notifications);
        return sessionIds;
    }

    /**
     * @param {number} id
     * @param {{ extra?; boolean }} options
     */
    _to_store(ids, store, { extra } = {}) {
        const kwargs = getKwArgs(arguments, "ids", "store", "extra");
        ids = kwargs.ids;
        extra = kwargs.extra;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        for (const rtcSession of this.browse(ids)) {
            const [data] = this._read_format(rtcSession.id, [], makeKwArgs({ load: false }));
            data.channel_member_id = mailDataHelpers.Store.one(
                DiscussChannelMember.browse(rtcSession.channel_member_id),
                makeKwArgs({ fields: { channel: [], persona: ["name", "im_status"] } })
            );
            if (extra) {
                Object.assign(data, {
                    is_camera_on: rtcSession.is_camera_on,
                    is_deaf: rtcSession.is_deaf,
                    is_muted: rtcSession.is_muted,
                    is_screen_sharing_on: rtcSession.is_screen_sharing_on,
                });
            }
            store.add(this.browse(rtcSession.id), data);
        }
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
            data: new mailDataHelpers.Store(DiscussChannelRtcSession.browse(id)).get_result(),
            channelId: channel.id,
        });
    }
}
