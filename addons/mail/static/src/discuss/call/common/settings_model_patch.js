import { ResUsersSettings } from "@mail/core/common/model_definitions";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Settings} */
const SettingsPatch = {
    /** @param {import("models").RtcSession} rtcSession */
    getVolume(rtcSession) {
        return (
            rtcSession.volume ??
            this.volumes.find(
                (volume) =>
                    volume.partner_id?.eq(rtcSession.partner_id) ||
                    volume.guest_id?.eq(rtcSession.guest_id)
            )?.volume ??
            0.5
        );
    },
};
patch(ResUsersSettings.prototype, SettingsPatch);
