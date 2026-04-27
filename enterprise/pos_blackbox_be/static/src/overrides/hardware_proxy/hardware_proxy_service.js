import { HardwareProxy } from "@point_of_sale/app/hardware_proxy/hardware_proxy_service";
import { patch } from "@web/core/utils/patch";

patch(HardwareProxy.prototype, {
    async openCashbox(action = false) {
        this.pos.increaseCashboxOpeningCounter();
        return super.openCashbox(...arguments);
    },
});
