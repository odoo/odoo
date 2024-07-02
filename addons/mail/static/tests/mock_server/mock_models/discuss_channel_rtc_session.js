import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { getKwArgs, models } from "@web/../tests/web_test_helpers";

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
        const rtcSessions = this._filter([["id", "in", sessionIds]]);
        /** @type {Record<string, DiscussChannelRtcSession>} */
        const sessionsByChannelId = {};
        for (const session of rtcSessions) {
            const [member] = DiscussChannelMember._filter([["id", "=", session.channel_member_id]]);
            if (!sessionsByChannelId[member.channel_id]) {
                sessionsByChannelId[member.channel_id] = [];
            }
            sessionsByChannelId[member.channel_id].push(session);
        }
        const notifications = [];
        for (const [channelId, sessions] of Object.entries(sessionsByChannelId)) {
            const [channel] = DiscussChannel.search_read([["id", "=", Number(channelId)]]);
            const store = new mailDataHelpers.Store("Thread", {
                id: channel.id,
                model: "discuss.channel",
                rtcSessions: [["ADD", sessions.map((session) => ({ id: session.id }))]],
            });
            store.add(sessions.map((session) => session.id));
            notifications.push([channel, "mail.record/insert", store.get_result()]);
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

        const rtcSessions = this._filter([["id", "in", ids]]);
        for (const rtcSession of rtcSessions) {
            store.add(
                DiscussChannelMember.browse(rtcSession.channel_member_id).map((record) => record.id)
            );
            const vals = {
                id: rtcSession.id,
                channelMember: { id: rtcSession.channel_member_id },
            };
            if (extra) {
                Object.assign(vals, {
                    isCameraOn: rtcSession.is_camera_on,
                    isDeaf: rtcSession.is_deaf,
                    isSelfMuted: rtcSession.is_self_muted,
                    isScreenSharingOn: rtcSession.is_screen_sharing_on,
                });
            }
            store.add("RtcSession", vals);
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
        const [session] = DiscussChannelRtcSession._filter([["id", "=", id]]);
        const [member] = DiscussChannelMember._filter([["id", "=", session.channel_member_id]]);
        const [channel] = DiscussChannel.search_read([["id", "=", member.channel_id]]);
        BusBus._sendone(channel, "discuss.channel.rtc.session/update_and_broadcast", {
            data: new mailDataHelpers.Store(
                DiscussChannelRtcSession.browse(id).map((record) => record.id)
            ).get_result(),
            channelId: channel.id,
        });
    }
}
