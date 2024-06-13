import { getKwArgs, models } from "@web/../tests/web_test_helpers";

export class DiscussChannelRtcSession extends models.ServerModel {
    _name = "discuss.channel.rtc.session";

    create() {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];

        const sessionIds = super.create(...arguments);
        const channelInfo = this._mail_rtc_session_format_by_channel(sessionIds);
        const notifications = [];
        for (const [channelId, sessionData] of Object.entries(channelInfo)) {
            const [channel] = DiscussChannel.search_read([["id", "=", Number(channelId)]]);
            notifications.push([
                channel,
                "discuss.channel/rtc_sessions_update",
                { id: channel.id, rtcSessions: [["ADD", sessionData]] },
            ]);
        }
        BusBus._sendmany(notifications);
        return sessionIds;
    }

    /**
     * @param {number} id
     * @param {{ extra?; boolean }} options
     */
    _mail_rtc_session_format(id, { extra } = {}) {
        const kwargs = getKwArgs(arguments, "id", "extra");
        id = kwargs.id;
        delete kwargs.id;
        extra = kwargs.extra;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const [rtcSession] = this._filter([["id", "=", id]]);
        const vals = {
            id: rtcSession.id,
            channelMember: DiscussChannelMember._discuss_channel_member_format([
                rtcSession.channel_member_id,
            ])[0],
        };
        if (extra) {
            Object.assign(vals, {
                isCameraOn: rtcSession.is_camera_on,
                isDeaf: rtcSession.is_deaf,
                isSelfMuted: rtcSession.is_self_muted,
                isScreenSharingOn: rtcSession.is_screen_sharing_on,
            });
        }
        return vals;
    }

    /**
     * @param {number[]} ids
     * @param {boolean} extra
     */
    _mail_rtc_session_format_by_channel(ids, extra) {
        const kwargs = getKwArgs(arguments, "ids", "extra");
        ids = kwargs.ids;
        delete kwargs.ids;
        extra = kwargs.extra;

        /** @type {import("mock_models").DiscussChanneleMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const rtcSessions = this._filter([["id", "in", ids]]);
        /** @type {Record<string, any>} */
        const data = {};
        for (const rtcSession of rtcSessions) {
            const [member] = DiscussChannelMember.read(rtcSession.channel_member_id);
            if (!data[member.channel_id[0]]) {
                data[member.channel_id[0]] = [];
            }
            data[member.channel_id[0]].push(this._mail_rtc_session_format(rtcSession.id, extra));
        }
        return data;
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

        this.write([id], values);
        const sessionData = this._mail_rtc_session_format(id);
        const [channel] = DiscussChannel.search_read([
            ["id", "=", sessionData.channelMember.thread.id],
        ]);
        BusBus._sendone(channel, "discuss.channel.rtc.session/update_and_broadcast", {
            data: sessionData,
            channelId: channel.id,
        });
    }
}
