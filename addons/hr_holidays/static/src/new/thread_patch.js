/* @odoo-module */

import { Thread } from "@mail/new/core_ui/thread";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "hr_holidays", {
    setup() {
        this._super();
        this.personaService = useService("mail.persona");
    },
});
