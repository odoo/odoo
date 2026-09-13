/** @odoo-module native */
import { waitImages } from "@point_of_sale/utils";
import { makeLogger } from "@web/core/debug/debug_logger";
import { SignalStore } from "@web/core/utils/reactive";

import { logPosMessage } from "../utils/pretty_console_log.js";
export const printerService = {
    dependencies: ["renderer"],
    start(env, { renderer }) {
        return new PrinterService(env, { renderer });
    },
};
const log = makeLogger("pos.printer");

export class PrinterService extends SignalStore {
    constructor(...args) {
        super(...args);
        this.setup(...args);
    }
    setup(env, { renderer }) {
        this.renderer = renderer;
        this.device = null;
        this.state = { isPrinting: false };
        this.printJobs = 0;
    }
    setPrinter(newDevice) {
        if (newDevice !== this.device) {
            log.lifecycle("setPrinter", () => ({
                from: this.device?.constructor?.name,
                to: newDevice?.constructor?.name,
            }));
        }
        this.device = newDevice;
    }
    async printWeb(el) {
        log.pipeline("printWeb", () => ({ tag: el?.tagName }));
        await this.renderer.whenMounted({
            el,
            callback: async (el) => {
                await waitImages(el);
                window.print(el);
            },
        });
        return true;
    }
    async printHtml(el, { webPrintFallback = false } = {}) {
        if (!this.device) {
            log.logic("printHtml: no device", () => ({ webPrintFallback }));
            return webPrintFallback && this.printWeb(el);
        }
        const endDevice = log.perf("printHtml: device.printReceipt");
        const printResult = await this.device.printReceipt(el);
        endDevice({
            successful: printResult.successful,
            errorCode: printResult.errorCode,
            warningCode: printResult.warningCode,
        });
        if (printResult.successful) {
            return printResult;
        }
        throw {
            title: printResult.message.title || "Error",
            body: printResult.message.body,
            canRetry: printResult.canRetry,
            errorCode: printResult.errorCode,
        };
    }
    async print(component, props, options = {}) {
        if (!this.device && !options?.webPrintFallback) {
            logPosMessage(
                "PrinterService",
                "print",
                "No printer device available and webPrintFallback is not enabled",
            );
            return;
        }
        this.printJobs++;
        this.state.isPrinting = true;
        const endPrint = log.perf(`print ${component.name}`);
        log.pipeline("print", () => ({
            component: component.name,
            device: Boolean(this.device),
            options,
        }));
        try {
            const endRender = log.perf(`print: render ${component.name}`);
            const el = await this.renderer.toHtml(component, props);
            endRender();
            try {
                await waitImages(el);
            } catch (e) {
                logPosMessage(
                    "PrinterService",
                    "print",
                    "Images could not be loaded correctly",
                    false,
                    [e],
                );
            }
            return await this.printHtml(el, options);
        } finally {
            this.state.isPrinting = --this.printJobs > 0;
            endPrint();
        }
    }
    is = () => Boolean(this.device?.printReceipt);
}
