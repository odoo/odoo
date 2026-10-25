import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { EcpayCertificateReceipt } from "@l10n_tw_edi_ecpay_pos/app/components/order_receipt/ecpay_certificate_receipt";
import { EcpayTransactionReceipt } from "@l10n_tw_edi_ecpay_pos/app/components/order_receipt/ecpay_transaction_receipt";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;
const CONSOLE_COLOR = "#F5B427";

patch(PosStore.prototype, {
    async _getUniformInvoiceData(order, options = {}) {
        const uniform_invoice = await this.data.call(
            "pos.order",
            "l10n_tw_edi_get_uniform_invoice",
            [order.id]
        );

        if (uniform_invoice) {
            if (uniform_invoice.ecpay_error && order.is_invoiced) {
                order.ecpay_error = uniform_invoice.ecpay_error;
                if (options.throw) {
                    await this.dialog.add(AlertDialog, {
                        title: _t("ECPay connection error"),
                        body:
                            _t(
                                "\n Unable to upload the e-invoice due to `Error`. Please make necessary changes and submit the invoice again."
                            ) + uniform_invoice.ecpay_error.replace(/<[^>]*>/g, ""),
                    });
                } else {
                    logPosMessage(
                        "Store",
                        "syncAllOrders",
                        "Unable to upload the e-invoice due to `Error`. Please make necessary changes and submit the invoice again.",
                        CONSOLE_COLOR
                    );
                }
                return;
            }
            order.invoice_month = uniform_invoice.invoice_month;
            order.iis_number = uniform_invoice.iis_number;
            order.iis_create_date = DateTime.fromSQL(uniform_invoice.iis_create_date, {
                zone: "utc",
            })
                .toLocal()
                .toFormat("yyyy-MM-dd HH:mm:ss");
            order.iis_random_number = uniform_invoice.iis_random_number;
            order.iis_tax_amount = uniform_invoice.iis_tax_amount;
            order.l10n_tw_edi_invoice_amount = uniform_invoice.l10n_tw_edi_invoice_amount;
            order.iis_identifier = uniform_invoice.iis_identifier;
            order.iis_carrier_type = uniform_invoice.iis_carrier_type;
            order.iis_carrier_num = uniform_invoice.iis_carrier_num;
            order.iis_category = uniform_invoice.iis_category;
            order.l10n_tw_edi_ecpay_seller_identifier =
                uniform_invoice.l10n_tw_edi_ecpay_seller_identifier;
            order.pos_barcode = uniform_invoice.pos_barcode;
            order.qrcode_left = uniform_invoice.qrcode_left;
            order.qrcode_right = uniform_invoice.qrcode_right;
            order.company_logo_exist = uniform_invoice.company_logo_exist;
        }
    },

    async syncAllOrders(options = {}) {
        const result = await super.syncAllOrders(options);
        if (result && result.length) {
            for (const order of result) {
                if (order?.isPrintEcpayInvoice) {
                    await this._getUniformInvoiceData(order, options);
                }
            }
        }
        return result;
    },

    async printReceipt({
        basic = false,
        order = this.getOrder(),
        printBillActionTriggered = false,
    } = {}) {
        const isOffline = this.data.network.offline;

        if (!isOffline && order?.isPrintEcpayInvoice && !order.ecpay_error) {
            await this._getUniformInvoiceData(order, { throw: true });
        }
        const result = await super.printReceipt({ basic, order, printBillActionTriggered });
        if (result && !isOffline && order?.isPrintEcpayInvoice && !order.ecpay_error) {
            await this.printer.print(
                EcpayCertificateReceipt,
                {
                    order,
                },
                this.printOptions
            );
            await this.printer.print(
                EcpayTransactionReceipt,
                {
                    order,
                },
                this.printOptions
            );
        }
        return result;
    },
});
