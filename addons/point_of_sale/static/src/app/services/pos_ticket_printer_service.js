import { registry } from "@web/core/registry";
import { EpsonPrinter } from "../utils/printer/epson_printer";
import { GeneratePrinterData } from "../utils/printer/generate_printer_data";
import { RetryPrintPopup } from "../components/popups/retry_print_popup/retry_print_popup";
import { _t } from "@web/core/l10n/translation";
import { renderToElement, renderToString } from "@web/core/utils/render";
import { toCanvas } from "../utils/html-to-image";
import { logPosImage } from "../utils/pretty_console_log";

export const posTicketPrinterService = {
    dependencies: ["dialog", "pos_data", "notification"],
    async start(env, dependencies) {
        const service = new PosTicketPrinterService(env, dependencies);
        await service.initPrinters();
        return service;
    },
};

export class PosTicketPrinterService {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, { dialog, pos_data, notification }) {
        this.env = env;
        this.dialog = dialog;
        this.notification = notification;
        this.data = pos_data;
    }

    get printers() {
        return [...this.preparationPrinters, ...this.receiptPrinters];
    }

    get useLna() {
        return this.printers.find((p) => p.use_lna);
    }

    get config() {
        return this.data.models["pos.config"].getFirst();
    }

    get session() {
        return this.data.models["pos.session"].getFirst();
    }

    get receiptPrinters() {
        return this.config.receipt_printer_ids;
    }

    get preparationPrinters() {
        return this.config.preparation_printer_ids;
    }

    get hasReceiptPrinters() {
        return this.receiptPrinters.length > 0;
    }

    get hasPreparationPrinters() {
        return this.preparationPrinters.length > 0;
    }

    getGenerator() {
        return new GeneratePrinterData(...arguments);
    }

    getOrderReceiptData(order, basic = false) {
        const generator = this.getGenerator({
            models: this.data.models,
            basicReceipt: basic,
            order,
        });
        return generator.generateReceiptData();
    }

    printWeb(iframe) {
        // By default ticket scale will be full width, when printing
        // this can be changed from the print dialog
        if (odoo.debug === "assets") {
            this.generateImage(iframe).then((image) => {
                logPosImage(image);
            });
        }

        iframe.contentWindow.focus();
        iframe.contentWindow.print();
    }

    showPrinterErrorDialog(message, retryFunction, fallbackFunction = undefined) {
        return this.dialog.add(RetryPrintPopup, {
            title: message.title,
            message: message.body,
            canRetry: true,
            retry: retryFunction,
            download: fallbackFunction,
        });
    }

    async openCashbox() {
        if (!this.config.default_receipt_printer_id?._instance?.openCashbox) {
            return false;
        }

        return await this.config.default_receipt_printer_id._instance.openCashbox();
    }

    async print({ printer, iframe, image = null }) {
        const finalImage = image || (await this.generateImage(iframe, printer));
        let status;
        try {
            status = await printer._instance.print(finalImage);
        } catch {
            status = {
                successful: false,
                message: { body: _t("An unexpected error occurred while printing.") },
            };
        }

        return status;
    }

    async printWithFallback({
        iframe,
        image = null,
        webFallback = true,
        printer = this.config.default_receipt_printer_id,
        fallbacks = this.config.receipt_printer_ids,
    } = {}) {
        if (!printer) {
            webFallback && this.printWeb(iframe);
            return;
        }

        const defaultPrinter = printer;
        const fallbackPrinters = fallbacks.filter((p) => p.id !== defaultPrinter.id);
        let status = { successful: false };

        for (const printer of [defaultPrinter, ...fallbackPrinters]) {
            try {
                status = await this.print({ printer, iframe, image });
                if (status.successful) {
                    break;
                }
            } catch (error) {
                console.error(`Printing failed on printer ${printer.name}:`, error);
            }
        }

        if (!status.successful) {
            this.showPrinterErrorDialog(
                status.message,
                () => this.printWithFallback(...arguments),
                () => this.printWeb(iframe)
            );
        }

        return status;
    }

    /**
     * All bellow method are using the default receipt printer but can
     * fallback to another printer if needed.
     * - this.config.default_receipt_printer_id
     * - this.config.receipt_printer_ids
     */
    async printSaleDetailsReceipt({ webFallback = true } = {}) {
        const generator = this.getGenerator({ models: this.data.models });
        const saleDetails = await this.data.call(
            "report.point_of_sale.report_saledetails",
            "get_sale_details",
            [false, false, false, [this.session.id]]
        );
        const data = generator.generateSaleDetailsData(saleDetails);
        const iframe = await this.generateIframe("point_of_sale.pos_sale_details_receipt", data);
        return await this.printWithFallback({ iframe, webFallback });
    }

    async printTipReceipt({ order, name, webFallback = true }) {
        const generator = this.getGenerator({ models: this.data.models, order });
        const data = generator.generateTipData(name);
        const iframe = await this.generateIframe("point_of_sale.pos_tip_receipt", data);
        return await this.printWithFallback({ iframe, webFallback });
    }

    async printCashMoveReceipt({
        reason,
        translatedType,
        order,
        formattedAmount,
        webFallback = true,
    }) {
        const printer = this.config.default_receipt_printer_id;
        if (!printer) {
            return;
        }

        const generator = this.getGenerator({ models: this.data.models, order });
        const data = generator.generateCashMoveData({ reason, translatedType, formattedAmount });
        const iframe = await this.generateIframe("point_of_sale.pos_cash_move_receipt", data);
        return await this.printWithFallback({ iframe, webFallback });
    }

    async printOrderReceipt({
        order,
        basic = false,
        printBillActionTriggered = false,
        webFallback = true,
    } = {}) {
        const data = this.getOrderReceiptData(order, basic);
        const iframe = await this.generateIframe("point_of_sale.pos_order_receipt", data);
        const result = await this.printWithFallback({ iframe, webFallback });

        if (!printBillActionTriggered && result) {
            await this.markReceiptAsPrinted(order);
        } else if (!order.nb_print) {
            order.nb_print = 0;
        }

        if (result?.warningCode) {
            this.displayPrinterWarning(result, _t("Receipt Printer"));
        }

        return result;
    }

    /**
     * Changes use preparation printers via this.config.preparation_printer_ids
     */
    async printOrderChanges({ order, opts = {}, printers = this.config.preparation_printer_ids }) {
        let isPrinted = false;
        const unsuccessfulPrints = [];
        const retryPrinters = new Set();

        for (const printer of printers) {
            const template = "point_of_sale.pos_order_change_receipt";
            const generator = this.getGenerator({ models: this.data.models, order });
            const categoryIds = new Set(printer.product_categories_ids.map((c) => c.id));
            const changes = generator.generatePreparationData(categoryIds, opts);

            for (const ticket of changes) {
                if (ticket.extra_data.reprint && !opts.explicitReprint) {
                    continue;
                }

                if (!printer?._instance) {
                    unsuccessfulPrints.push(printer.name + " is not connected");
                    break;
                }

                const iframe = await this.generateIframe(template, ticket);
                const image = await this.generateImage(iframe, printer);
                const result = await this.print({ printer, image });
                if (result.successful) {
                    isPrinted = true;
                }

                if (!result.successful) {
                    retryPrinters.add(printer);
                    unsuccessfulPrints.push(printer.name + ": " + result.message.body);
                } else if (result.warningCode) {
                    this.displayPrinterWarning(result, printer.name);
                }
            }
        }

        if (unsuccessfulPrints.length) {
            const message = {
                title: _t("Printing failed"),
                body: unsuccessfulPrints.join("\n"),
            };
            this.showPrinterErrorDialog(message, () => this.printOrderChanges(...arguments));
        }

        return isPrinted;
    }

    /**
     * Helpers for printer initialization, warnings messages and
     * data generation.
     */
    displayPrinterWarning(printResult, printerName) {
        let notification;
        if (printResult.warningCode === "ROLL_PAPER_HAS_ALMOST_RUN_OUT") {
            notification = _t("%s almost runs out of paper.", printerName);
        }
        if (notification) {
            this.notification.add(notification, {
                type: "warning",
            });
        }
    }

    async initPrinters() {
        const printers = [...this.preparationPrinters, ...this.receiptPrinters];
        for (const printer of printers) {
            const instance = await this.createPrinterInstance(printer);
            printer._instance = instance;
        }
    }

    async createPrinterInstance(printer) {
        if (printer.printer_type === "epson_epos") {
            return new EpsonPrinter({ printer });
        }

        return false;
    }

    async getHtmlFromComponent(ComponentClass, data) {
        const container = document.getElementById("receipt-iframe-container");
        container.innerHTML = "";
        const root = renderToString.app.createRoot(ComponentClass, { props: data });
        await root.mount(container);
        const result = container.innerHTML;
        root.destroy();
        return result;
    }

    async generateIframe(template, data) {
        const container = document.getElementById("receipt-iframe-container");
        const iframe = document.createElement("iframe");
        const el = renderToElement(template, data);
        iframe.style.width = "100%";
        iframe.style.height = "100%";
        iframe.style.border = "none";
        iframe.srcdoc = el.outerHTML;
        container.innerHTML = "";
        container.appendChild(iframe);
        await new Promise((resolve) => (iframe.onload = resolve));
        return iframe;
    }

    createReceiptStyle({ iframeEl, printer }) {
        const iframeHead = iframeEl.querySelector("head");
        iframeHead.querySelector("#printer-receipt-style")?.remove();
        const { maxWidth, fontSize } = printer._instance.getStyle();

        const style = document.createElement("style");
        style.id = "printer-receipt-style";

        const LINE_HEIGHT_RATIO = 1.4;

        const getFontRules = (multiplier) => {
            const size = fontSize * multiplier;
            const height = size * LINE_HEIGHT_RATIO;
            return `
                font-size: ${size}px !important;
                line-height: ${height}px !important;
            `;
        };

        const cssRules = `
            #pos-receipt { width: ${maxWidth}px !important; font-size: ${fontSize}px !important; }
            /** Text classes **/
            #pos-receipt .text-small { ${getFontRules(0.8)} }
            #pos-receipt .text-normal { ${getFontRules(1.0)} }
            #pos-receipt .text-large { ${getFontRules(1.2)} }
            #pos-receipt .text-insane { ${getFontRules(2.2)} }
        `;

        style.textContent = cssRules;
        iframeHead.appendChild(style);
    }

    async generateImage(iframe, printer) {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        const iframeEl = doc.getElementById("pos-receipt");
        this.createReceiptStyle({ iframeEl, printer });
        const sizes = iframeEl.getBoundingClientRect();
        const image = await toCanvas(iframeEl, {
            backgroundColor: "#ffffff",
            height: Math.ceil(sizes.height),
            width: Math.ceil(sizes.width),
            pixelRatio: 1,
        });

        logPosImage(image);
        return image;
    }

    async markReceiptAsPrinted(order) {
        const count = order.nb_print ? order.nb_print + 1 : 1;
        if (order.isSynced) {
            const wasDirty = order.isDirty();
            await this.data.write("pos.order", [order.id], { nb_print: count });
            if (!wasDirty) {
                order._dirty = false;
            }
        } else {
            order.nb_print = count;
        }
    }
}

registry.category("services").add("pos_ticket_printer", posTicketPrinterService);
