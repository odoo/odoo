/* @odoo-module */

import { Thread } from "@mail/core_ui/thread";
import { createLocalId } from "@mail/utils/misc";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "hr_holidays", {
    setup() {
        this._super();
        this.personaService = useService("mail.persona");
        this.discussStore = useService("discuss.store");
    },
    getChannel() {
        return this.discussStore.channels[createLocalId("discuss.channel", this.props.thread.id)];
    },
});
