import { Persona } from "@mail/core/common/persona_model";
import { Record } from "@mail/model/record";
import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    setup() {
        super.setup(...arguments);
        this.currentRtcSession = Record.one("discuss.channel.rtc.session", { inverse: "persona" });
    },
});
