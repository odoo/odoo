import { Settings } from "@mail/core/common/settings_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Settings} */
const SettingsPatch = {
    setup() {
        super.setup(...arguments);
    },
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
patch(Settings.prototype, SettingsPatch);
