import { patch } from "@web/core/utils/patch";
import { PosStore, posService } from "@point_of_sale/app/store/pos_store";
import { isFiscalPrinterActive, isFiscalPrinterConfigured } from "./helpers/utils";

patch(posService, {
    dependencies: [...posService.dependencies, "epson_fiscal_printer"],
});

patch(PosStore.prototype, {
    async setup(env, { epson_fiscal_printer }) {
        await super.setup(...arguments);
        if (isFiscalPrinterActive(this.config)) {
            const { it_fiscal_printer_https, it_fiscal_printer_ip } = this.config;
            this.fiscalPrinter = epson_fiscal_printer(
                it_fiscal_printer_https,
                it_fiscal_printer_ip
            );
            this.fiscalPrinter.getPrinterSerialNumber().then((sn) => {
                this.config.it_fiscal_printer_serial_number = sn;
            });
        }
    },
    getSyncAllOrdersContext(orders, options = {}) {
        const context = super.getSyncAllOrdersContext(orders, options);
        if (isFiscalPrinterActive(this.config)) {
            // No need to slow down the order syncing by generating the PDF in the server.
            // The invoice will be printed by the fiscal printer.
            context["generate_pdf"] = false;
        }
        return context;
    },
    // override
    async printReceipt({
        basic = false,
        order = this.get_order(),
        printBillActionTriggered = false,
    } = {}) {
        if (!isFiscalPrinterActive(this.config)) {
            return super.printReceipt(...arguments);
        }
        let printResult = {};
        const updateData = {
            // Increment nb_print, handling initial undefined/zero case
            nb_print: (order.nb_print || 0) + 1,
        };
        const isFiscal = !basic && !printBillActionTriggered;

        if (!isFiscal) {
            printResult = await this.fiscalPrinter.printNonFiscalReceipt({
                isBasicPrint: basic,
                isEarlyPrint: printBillActionTriggered,
            });
        } else if (!order.nb_print) {
            try {
                printResult = order.to_invoice
                    ? await this.fiscalPrinter.printFiscalInvoice({ order })
                    : await this.fiscalPrinter.printFiscalReceipt({ order });
            } catch (error) {
                printResult.success = false;
                if (!this.data.network.offline) {
                    throw error;
                }
            }

            if (printResult.success) {
                Object.assign(updateData, {
                    it_fiscal_receipt_number: printResult.addInfo.fiscalReceiptNumber,
                    it_fiscal_receipt_date: printResult.addInfo.fiscalReceiptDate,
                    it_z_rep_number: printResult.addInfo.zRepNumber,
                });
                if (this.config.it_fiscal_cash_drawer) {
                    await this.fiscalPrinter.openCashDrawer();
                }
            }
        } else {
            printResult = await this.fiscalPrinter.printContentByNumbers({
                order: order,
            });
        }

        if (printResult.success && isFiscal) {
            await this.data.write("pos.order", [order.id], updateData);
            return true;
        }
    },

    // EXTENDS 'point_of_sale'
    prepareProductBaseLineForTaxesComputationExtraValues(product, p = false) {
        const extraValues = super.prepareProductBaseLineForTaxesComputationExtraValues(product, p);
        extraValues.l10n_it_epson_printer = isFiscalPrinterConfigured(this.config);
        return extraValues;
    },
});
