import { Component, useProps, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { EpsonPrinter } from "@point_of_sale/app/utils/printer/epson_printer";
import { initLNA } from "@point_of_sale/app/utils/init_lna";

export class PrintReceipt extends Component {
    static template = "point_of_sale.PrintReceiptButton";
    props = useProps(standardWidgetProps);

    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.state = proxy({
            isPrinting: false,
        });
    }

    async createPrinterInstance(printer) {
        if (printer.printer_type === "epson_epos") {
            return new EpsonPrinter({ printer });
        }
        return false;
    }

    printerStorageKey(configId) {
        return `pos_default_printer_id_${configId}_${odoo.info?.db}`;
    }

    selectPrinter(printers, storageKey) {
        const storedId = Number(localStorage.getItem(storageKey));
        const storedPrinter = printers.find((printer) => printer.id === storedId);
        if (storedPrinter) {
            return storedPrinter;
        }
        if (printers.length > 0) {
            return printers[0];
        }
        return false;
    }

    async onClick() {
        this.state.isPrinting = true;
        try {
            const printData = await this.orm.call("pos.order", "get_receipt_print_data", [
                [this.props.record.resId],
            ]);
            await this.printReceipt(printData);
        } finally {
            this.state.isPrinting = false;
        }
    }

    async printReceipt({ printers, receipt_html, config_id }) {
        for (const printer of printers) {
            printer._instance = await this.createPrinterInstance(printer);
        }
        const usablePrinters = printers.filter((printer) => printer._instance);
        if (!usablePrinters.length) {
            this.printWeb(receipt_html);
            await this.markReceiptAsPrinted();
            return;
        }

        if (usablePrinters.some((printer) => printer.use_lna)) {
            await initLNA(this.notification);
        }

        const defaultPrinter = this.selectPrinter(
            usablePrinters,
            this.printerStorageKey(config_id)
        );
        const printersToTry = defaultPrinter
            ? [defaultPrinter, ...usablePrinters.filter((p) => p.id !== defaultPrinter.id)]
            : usablePrinters;

        let status;
        for (const printer of printersToTry) {
            status = await printer._instance.print(printer.receipt);
            if (status.successful) {
                this.notification.add(_t("Receipt sent to %s.", printer.name), {
                    type: "success",
                });
                await this.markReceiptAsPrinted();
                return;
            }
        }
        await this.markReceiptAsPrinted();
        this.printWeb(receipt_html);
        this.notification.add(status.message.body, {
            title: status.message.title,
            type: "danger",
        });
    }

    async markReceiptAsPrinted() {
        await this.orm.call("pos.order", "mark_receipt_as_printed", [[this.props.record.resId]]);
    }

    printWeb(html) {
        const iframe = document.createElement("iframe");
        iframe.style = "position: absolute; left: -9999px; top: 0; border: none;";
        iframe.srcdoc = html;
        iframe.onload = () => {
            iframe.contentWindow.onafterprint = () => iframe.remove();
            iframe.contentWindow.focus();
            iframe.contentWindow.print();
        };
        document.body.appendChild(iframe);
    }
}

export const PrintReceiptWidget = {
    component: PrintReceipt,
};
registry.category("view_widgets").add("point_of_sale_print_receipt", PrintReceiptWidget);
