/** @odoo-module */

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.visitor = Record.one("Persona");
    },
    update(data) {
        super.update(data);
        if (data?.visitor) {
            this.visitor = data.visitor;
        }
        assignDefined(this, data, ["requested_by_operator"]);
    },
});
