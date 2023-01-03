/** @odoo-module */

import Chrome from "@point_of_sale/js/Chrome";
import Registries from "@point_of_sale/js/Registries";

const PosSixChrome = (Chrome) =>
    class extends Chrome {
        get balanceButtonIsShown() {
            return this.env.pos.payment_methods.some((pm) => pm.use_payment_terminal === "six");
        }
    };

Registries.Component.extend(Chrome, PosSixChrome);

export default Chrome;
