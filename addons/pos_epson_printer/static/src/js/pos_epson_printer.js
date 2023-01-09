/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/js/models";
import EpsonPrinter from "@pos_epson_printer/js/printers";
import Registries from "@point_of_sale/js/Registries";

const PosEpsonPosGlobalState = (PosGlobalState) =>
    class PosEpsonPosGlobalState extends PosGlobalState {
        after_load_server_data() {
            var self = this;
            return super.after_load_server_data(...arguments).then(function () {
                if (self.config.other_devices && self.config.epson_printer_ip) {
                    self.env.proxy.printer = new EpsonPrinter(self.config.epson_printer_ip, self);
                }
            });
        }
    };
Registries.Model.extend(PosGlobalState, PosEpsonPosGlobalState);
