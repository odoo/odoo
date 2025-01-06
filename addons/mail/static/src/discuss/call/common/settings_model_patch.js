import { Settings } from "@mail/core/common/settings_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Settings} */
const SettingsPatch = {
    setup() {
        super.setup(...arguments);
    },
    getVolume(rtcSession) {
        return (
            rtcSession.volume ||
            this.volumes.find(
                (volume) =>
                    (volume.persona.type === "partner" &&
                        volume.persona.id === rtcSession.partnerId) ||
                    (volume.persona.type === "guest" && volume.persona.id === rtcSession.guestId)
            )?.volume ||
            0.5
        );
    },
};
patch(Settings.prototype, SettingsPatch);
