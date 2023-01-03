/** @odoo-module */

import CashierName from "@point_of_sale/js/ChromeWidgets/CashierName";
import Registries from "@point_of_sale/js/Registries";
import SelectCashierMixin from "@pos_hr/js/SelectCashierMixin";
import { useBarcodeReader } from "@point_of_sale/js/custom_hooks";

const PosHrCashierName = (CashierName) =>
    class extends SelectCashierMixin(CashierName) {
        setup() {
            super.setup();
            useBarcodeReader({ cashier: this.barcodeCashierAction });
        }
        //@Override
        get avatar() {
            if (this.env.pos.config.module_pos_hr) {
                const cashier = this.env.pos.get_cashier();
                return `/web/image/hr.employee/${cashier.id}/avatar_128`;
            }
            return super.avatar;
        }
        //@Override
        get cssClass() {
            if (this.env.pos.config.module_pos_hr) {
                return { oe_status: true };
            }
            return super.cssClass;
        }
    };

Registries.Component.extend(CashierName, PosHrCashierName);

export default CashierName;
