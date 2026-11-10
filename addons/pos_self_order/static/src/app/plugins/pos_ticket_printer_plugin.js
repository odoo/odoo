import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterPlugin } from "@point_of_sale/app/plugins/pos_ticket_printer_plugin";
import { user } from "@web/core/user";
import { jsToPyLocale } from "@web/core/l10n/utils";
import { rpc } from "@web/core/network/rpc";

patch(PosTicketPrinterPlugin.prototype, {
    showPrinterErrorDialog(message, retryFunction, fallbackFunction = undefined) {
        return false;
    },
    async markReceiptAsPrinted(order) {
        return false;
    },
    async printOrderChanges({
        order,
        opts = {},
        printers = this.config.preparation_printer_ids,
        retryChanges = new Map(),
    }) {
        const lang = jsToPyLocale(user.lang);

        // When the frontend language is different from the default user language,
        // try to print via RPC first. This ensures that the receipt is printed in the
        // correct language and format for self-ordering scenarios. The backend will
        // always use the default user language for rendering receipts.
        const kioskPrinters =
            lang === this.config._default_user_lang
                ? printers
                : await this.printServerGeneratedOrderChanges(order, printers);

        // In case of failure, fallback to the default printing behavior
        if (kioskPrinters.length) {
            return super.printOrderChanges({ order, opts, printers: kioskPrinters, retryChanges });
        }
    },
    async printServerGeneratedOrderChanges(order, printers) {
        // The server doesn't return any receipt for label printer since it can generate it.
        // If there is a label printer, we call super with an arg to only print the label receipts.
        // The server receipts only fit 80mm paper, the other printers are also printed by super.
        const serverPrinters = printers.filter((printer) => printer.paper_size === "80");
        const kioskPrinters = printers.filter((printer) => printer.paper_size !== "80");
        if (!serverPrinters.length) {
            return kioskPrinters;
        }

        let receipts;
        try {
            ({ receipts } = await rpc(`/pos-self-order/kiosk/change-receipt/${order.id}`, {
                access_token: odoo.access_token,
                order_access_token: order.access_token,
            }));
        } catch {
            // Can be ignored on kiosk
            console.log(`Failed to print order changes for order ${order.id}`);
            return printers;
        }

        for (const printer of serverPrinters) {
            const images = receipts[printer.id];
            if (images && !images.length) {
                kioskPrinters.push(printer);
                continue;
            }

            for (const image of images ?? []) {
                // No needs to monitor print error since in kiosk mode the frontend disables
                // error dialogs. See showPrinterErrorDialog.
                // Convert from base64 to canvas to be compatible with iMin and IoT printers.
                // If the server directly responds with Epson XML, it willn't be compatible.
                const canvas = await this.base64ToCanvas(image).catch(() => null);
                const result = canvas && (await this.print({ printer, image: canvas }));

                if (!result?.successful) {
                    // Will be retried in super, to know, if the last image of the printer failed
                    // super will reprint all of them. Its an acceptable behavior to ensure
                    // all images are printed correctly.
                    kioskPrinters.push(printer);
                    break;
                }
            }
        }
        return kioskPrinters;
    },
    async base64ToCanvas(base64) {
        const img = new Image();
        img.src = `data:image/jpeg;base64,${base64}`;
        await img.decode();
        const canvas = document.createElement("canvas");
        // The Epson raster encoder needs a width that is a multiple of 8
        canvas.width = img.width - (img.width % 8);
        canvas.height = img.height;
        canvas.getContext("2d").drawImage(img, 0, 0);
        return canvas;
    },
});
