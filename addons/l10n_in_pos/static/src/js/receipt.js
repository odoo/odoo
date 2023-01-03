/** @odoo-module */

import { Orderline } from "@point_of_sale/js/models";
import Registries from "@point_of_sale/js/Registries";

const L10nInOrderline = (Orderline) =>
    class L10nInOrderline extends Orderline {
        export_for_printing() {
            var line = super.export_for_printing(...arguments);
            line.l10n_in_hsn_code = this.get_product().l10n_in_hsn_code;
            return line;
        }
    };
Registries.Model.extend(Orderline, L10nInOrderline);
