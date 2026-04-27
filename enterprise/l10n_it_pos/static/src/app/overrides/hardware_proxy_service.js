import { HardwareProxy } from "@point_of_sale/app/hardware_proxy/hardware_proxy_service";
import { patch } from "@web/core/utils/patch";
import { isFiscalPrinterActive } from "./helpers/utils";

patch(HardwareProxy.prototype, {
    async openCashbox(action = false) {
        if (isFiscalPrinterActive(this.pos.config)) {
            return this.pos.fiscalPrinter.openCashDrawer();
        }
        return super.openCashbox(...arguments);
    },
});
