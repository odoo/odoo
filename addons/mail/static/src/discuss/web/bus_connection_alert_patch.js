import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { BusConnectionAlert } from "@mail/discuss/core/public_web/bus_connection_alert";

patch(BusConnectionAlert.prototype, {
    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
    },

    get showBorderOnFailure() {
        return super.showBorderOnFailure || this.store.discuss.isActive;
    },
});
