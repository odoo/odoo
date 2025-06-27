import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PrinterService } from "@base_printer/epson_printer/services/printer_service";
import { EpsonPrinter } from "@base_printer/epson_printer/printer/epson_printer";

export const lablelPrinterService = {
    dependencies: ["renderer", "dialog", "orm"],
    start(env, { renderer, dialog, orm }) {
        return new LablelPrinterService(env, { dialog, renderer, orm });
    },
};
class LablelPrinterService extends PrinterService {
    constructor(...args) {
        super(...args);
        this.setup(...args);
    }
    setup(env, { dialog, renderer, orm }) {
        super.setup(...arguments);
        this.renderer = renderer;
        this.dialog = dialog;
        this.orm = orm;
    }
    async print(component, props, options = {}, printerIp = "") {
        this.epson_printer_ip = printerIp;
        return await super.print(...arguments);
    }
    async printHtml() {
        const printer = new EpsonPrinter({ ip: this.epson_printer_ip });
        this.setPrinter(printer);
        try {
            return await super.printHtml(...arguments);
        } catch (error) {
            console.error(error);
            this.dialog.closeAll();
            this.dialog.add(AlertDialog, {
                title: error.title,
                body: error.body,
            });
        }
    }
}

registry.category("services").add("label_printer", lablelPrinterService);
