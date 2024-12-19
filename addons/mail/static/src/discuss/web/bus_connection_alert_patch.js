import { patch } from "@web/core/utils/patch";
import { BusConnectionAlert } from "@bus/components/bus_connection_alert";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(BusConnectionAlert.prototype, {
    setup() {
        super.setup(...arguments);
        this.store = useState(useService("mail.store"));
    },

    get showBorderOnFailure() {
        return super.showBorderOnFailure || this.store.discuss.isActive;
    },
});
