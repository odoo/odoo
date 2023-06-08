odoo.define('mk_fiscal_printer.mk_fiscal_printer', function (require) {
    "use strict";

    var FiscalPrinter = require('mk_fiscal_printer.Printer');
    const Registries = require('point_of_sale.Registries');
    var {Order, PosGlobalState} = require('point_of_sale.models');
    const Chrome = require('point_of_sale.Chrome');
    const ClosePosPopup = require('point_of_sale.ClosePosPopup');

    var fp = new Tremol.FP();
    var FiscalPos = null;
    const MkFiscalPrinterGlobalState = (PosGlobalState) => class MkFiscalPrinterGlobalState extends PosGlobalState {
        after_load_server_data() {
            var self = this;
            return super.after_load_server_data(...arguments).then(function () {
                console.log(self);
                if (self.config.fiscal_printer_ip) {
                    FiscalPos = new FiscalPrinter(self.config.fiscal_printer_ip, fp);
                }
            });
        }
    }

    const OrdersPrintFiscal = (Order) => class OrdersPrintFiscal extends Order {
        export_for_printing() {
            var result = super.export_for_printing(...arguments);
            console.log(result);
            try {
                FiscalPos.createOrder(result);
            } catch (err) {
                console.log(err);
            }
            return result;
        }
    }

    const PosResChrome = (Chrome) => class extends ClosePosPopup {
        async closeSession() {
            FiscalPos.PrintDailyReport();
            await super.closeSession();
        }
    }

    Registries.Model.extend(PosGlobalState, MkFiscalPrinterGlobalState)
    Registries.Model.extend(Order, OrdersPrintFiscal);
    Registries.Component.extend(ClosePosPopup, PosResChrome);
})