/* @odoo-module */

import { Messaging } from "@mail/core/messaging_service";
import { createLocalId } from "@mail/utils/misc";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

patch(Messaging.prototype, "discuss", {
    setup(env, services) {
        this._super(...arguments);
        /** @type {import("@mail/discuss/channel_member_service").ChannelMemberService} */
        this.channelMemberService = services["discuss.channel.member"];
        /** @type {import("@mail/discuss/rtc/rtc_service").Rtc} */
        this.rtc = services["mail.rtc"];
        /** @type {import("@mail/core/store_service").Store} */
        this.discussStore = services["discuss.store"];
    },
    /**
     * @override
     */
    handleNotification(notifications) {
        this._super(notifications);
        for (const notif of notifications) {
            switch (notif.type) {
                case "discuss.channel/rtc_sessions_update":
                    {
                        const { id, rtcSessions } = notif.payload;
                        const sessionsData = rtcSessions[0][1];
                        const command = rtcSessions[0][0];
                        this._updateRtcSessions(id, sessionsData, command);
                    }
                    break;
                case "discuss.channel/joined": {
                    const { channel, invited_by_user_id: invitedByUserId } = notif.payload;
                    const thread = this.threadService.insert({
                        ...channel,
                        model: "discuss.channel",
                        rtcSessions: undefined,
                        channel: channel.channel,
                        type: channel.channel.channel_type,
                    });
                    const rtcSessions = channel.rtcSessions;
                    const sessionsData = rtcSessions[0][1];
                    const command = rtcSessions[0][0];
                    this._updateRtcSessions(thread.id, sessionsData, command);

                    if (invitedByUserId && invitedByUserId !== this.store.user?.user?.id) {
                        this.notificationService.add(
                            sprintf(_t("You have been invited to #%s"), thread.displayName),
                            { type: "info" }
                        );
                    }
                    break;
                }
            }
        }
    },
    _updateRtcSessions(channelId, sessionsData, command) {
        const channel = this.discussStore.channels[createLocalId("discuss.channel", channelId)];
        if (!channel) {
            return;
        }
        const oldCount = Object.keys(channel.rtcSessions).length;
        switch (command) {
            case "insert-and-unlink":
                for (const sessionData of sessionsData) {
                    this.rtc.deleteSession(sessionData.id);
                }
                break;
            case "insert":
                for (const sessionData of sessionsData) {
                    const session = this.rtc.insertSession(sessionData);
                    channel.rtcSessions[session.id] = session;
                }
                break;
        }
        if (Object.keys(channel.rtcSessions).length > oldCount) {
            this.soundEffectsService.play("channel-join");
        } else if (Object.keys(channel.rtcSessions).length < oldCount) {
            this.soundEffectsService.play("member-leave");
        }
    },
});
