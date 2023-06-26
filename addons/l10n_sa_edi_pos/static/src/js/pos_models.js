/** @odoo-module **/

import { Order } from "@point_of_sale/js/models";
import Registries from "@point_of_sale/js/Registries";

export const L10nSAPosOrder = (Order) =>
    class L10nSAPosOrder extends Order {
        constructor() {
            super(...arguments);
            if (this.pos.company.country && this.pos.company.country.code === 'SA') {
                this.set_to_invoice(true);
            }
        }
    }

Registries.Model.extend(Order, L10nSAPosOrder);