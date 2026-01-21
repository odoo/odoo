import { Settings } from "@mail/core/common/settings_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Settings} */
const SettingsPatch = {
    setup() {
        super.setup();
        /** @type {boolean} */
        this.livechat_push;
    },
};

patch(Settings.prototype, SettingsPatch);
