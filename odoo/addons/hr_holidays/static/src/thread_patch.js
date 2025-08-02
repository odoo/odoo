/* @odoo-module */

import { Thread } from "@mail/core/common/thread";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.personaService = useService("mail.persona");
    },
});
