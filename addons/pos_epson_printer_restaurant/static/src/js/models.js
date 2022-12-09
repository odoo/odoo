/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/js/models";
import EpsonPrinter from "@pos_epson_printer/js/printers";
import Registries from "@point_of_sale/js/Registries";

// The override of create_printer needs to happen after its declaration in
// pos_restaurant. We need to make sure that this code is executed after the
// models file in pos_restaurant.
import "@pos_restaurant/js/models";

const PosEpsonResPosGlobalState = (PosGlobalState) =>
    class PosEpsonResPosGlobalState extends PosGlobalState {
        create_printer(config) {
            if (config.printer_type === "epson_epos") {
                return new EpsonPrinter(config.epson_printer_ip, this);
            } else {
                return super.create_printer(...arguments);
            }
        }
    };
Registries.Model.extend(PosGlobalState, PosEpsonResPosGlobalState);
