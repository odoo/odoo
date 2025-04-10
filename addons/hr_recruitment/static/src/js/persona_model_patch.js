import { Persona } from "@mail/core/common/persona_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    /** @override */
    setup() {
        super.setup(...arguments);
        this.applicant_ids = fields.Many("hr.applicant", { inverse: "partner_id" });
    },
});
