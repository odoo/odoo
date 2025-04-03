import { Persona } from "@mail/core/common/persona_model";
import { fields } from "@mail/model/misc";
import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    setup() {
        super.setup(...arguments);
        this.currentRtcSession = fields.One("discuss.channel.rtc.session", { inverse: "persona" });
    },
});
