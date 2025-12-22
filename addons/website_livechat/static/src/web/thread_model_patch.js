import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.visitor = Record.one("Persona");
        this.visitorPartner = Record.one("Persona");
    },
});
