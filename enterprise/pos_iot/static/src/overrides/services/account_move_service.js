import { patch } from "@web/core/utils/patch";
import { AccountMoveService } from "@account/services/account_move_service";
import { getSelectedPrintersForReport } from "@iot/iot_report_action";
import { uuidv4 } from "@point_of_sale/utils";

patch(AccountMoveService.prototype, {
    async downloadPdf(accountMoveId) {
        const [invoiceReport] = await this.orm.searchRead(
            "ir.actions.report",
            [["report_name", "=", "account.report_invoice_with_payments"]],
            ["id", "device_ids"]
        );
        if (!invoiceReport?.device_ids?.length) {
            return super.downloadPdf(...arguments);
        }

        const selectedPrinters = await getSelectedPrintersForReport(invoiceReport.id, this.env);
        if (!selectedPrinters) {
            return super.downloadPdf(...arguments);
        }

        const downloadAction = await this.orm.call("account.move", "action_invoice_download_pdf", [
            accountMoveId,
        ]);
        const pdfResponse = await fetch(downloadAction.url);
        const pdfBytes = new Uint8Array(await pdfResponse.arrayBuffer());
        const pdfByteString = pdfBytes.reduce(
            (currentString, nextByte) => (currentString += String.fromCharCode(nextByte)),
            ""
        );
        const base64String = btoa(pdfByteString);

        // TODO FW 18.4: use iot_http
        const printerDevices = await this.orm.call("ir.actions.report", "get_devices_from_ids", [
            null,
            selectedPrinters,
        ]);
        await this.orm.call(
            "ir.actions.report",
            "render_and_send",
            [invoiceReport.id, printerDevices, null, null, uuidv4(), true],
            {
                context: {
                    data_base64: base64String,
                },
            }
        );
    },
});
