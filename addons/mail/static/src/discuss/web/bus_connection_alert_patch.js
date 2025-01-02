import { patch } from "@web/core/utils/patch";
import { BusConnectionAlert } from "@bus/components/bus_connection_alert";
import { useService } from "@web/core/utils/hooks";

patch(BusConnectionAlert.prototype, {
    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
    },

    get showBorderOnFailure() {
        return super.showBorderOnFailure || this.store.discuss.isActive;
    },
});
