import { SoundEffects } from "@mail/core/common/sound_effects_service";
import { patch } from "@web/core/utils/patch";

patch(SoundEffects.prototype, {
    play() {
        this.soundEffects = {
            ...this.soundEffects,
            error: { path: "/point_of_sale/static/src/sounds/error" },
            bell: { path: "/point_of_sale/static/src/sounds/bell" },
            notification: { path: "/point_of_sale/static/src/sounds/notification" },
            beep: { path: "/point_of_sale/static/src/sounds/beep" },
            "order-receive-tone": {
                path: "/point_of_sale/static/src/sounds/order-receive-tone",
            },
        };
        super.play(...arguments);
    },
});
