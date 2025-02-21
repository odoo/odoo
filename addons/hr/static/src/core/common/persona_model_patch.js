import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    /** @type {number|undefined} */
    employeeId: undefined,
});
