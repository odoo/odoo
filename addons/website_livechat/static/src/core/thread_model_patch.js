/** @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if (data?.visitor) {
            this.visitor = this._store.Persona.insert({
                ...data.visitor,
                type: "visitor",
            });
        }
        assignDefined(this, data, ["requested_by_operator"]);
    },
});
