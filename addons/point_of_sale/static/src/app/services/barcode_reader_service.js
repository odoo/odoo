/** @odoo-module native */
import { BarcodeParser } from "@barcodes/js/barcode_parser";
import { GS1BarcodeError } from "@barcodes_gs1_nomenclature/js/barcode_parser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { Mutex } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { AlertDialog } from "@web/ui/dialog";

import { logPosMessage } from "../utils/pretty_console_log.js";

const log = makeLogger("pos.barcode");

export class BarcodeReader {
    static serviceDependencies = [
        "dialog",
        "hardware_proxy",
        "notification",
        "action",
        "orm",
    ];
    constructor(parser, { dialog, hardware_proxy, notification, action, orm }) {
        this.parser = parser;
        this.dialog = dialog;
        this.action = action;
        this.orm = orm;
        this.hardwareProxy = hardware_proxy;
        this.notification = notification;
        this.setup();
    }

    setup() {
        this.mutex = new Mutex();
        this.cbMaps = new Set();
        this.exclusiveRegistrations = [];
        this.remoteScanning = false;
        this.remoteActive = 0;
    }

    get exclusiveCbMap() {
        return this.exclusiveRegistrations.at(-1)?.cbMap ?? null;
    }

    register(cbMap, exclusive) {
        log.lifecycle("register", () => ({
            exclusive: Boolean(exclusive),
            types: Object.keys(cbMap),
            registered: this.cbMaps.size,
        }));
        const registration = { cbMap };
        if (exclusive) {
            this.exclusiveRegistrations.push(registration);
        } else {
            this.cbMaps.add(cbMap);
        }
        return () => {
            if (exclusive) {
                const index = this.exclusiveRegistrations.indexOf(registration);
                if (index !== -1) {
                    this.exclusiveRegistrations.splice(index, 1);
                }
            } else {
                this.cbMaps.delete(cbMap);
            }
            log.lifecycle("unregister", () => ({
                exclusive: Boolean(exclusive),
                exclusiveRemaining: this.exclusiveRegistrations.length,
                registered: this.cbMaps.size,
            }));
        };
    }

    scan(code) {
        return this.mutex.exec(() => this._scan(code));
    }
    async _scan(code) {
        log.pipeline("scan", () => ({ code, callbacks: this.cbMaps?.size }));
        if (!code) {
            return;
        }

        const cbMaps = this.exclusiveCbMap ? [this.exclusiveCbMap] : [...this.cbMaps];
        const endScan = log.perf("scan");

        let parseBarcode;
        try {
            parseBarcode = this.parser.parse_barcode(code);
            if (
                Array.isArray(parseBarcode) &&
                !parseBarcode.some((element) => element.type === "product")
            ) {
                throw new GS1BarcodeError("The GS1 barcode must contain a product.");
            }
        } catch (error) {
            if (error instanceof GS1BarcodeError) {
                log.logic("scan: gs1 error", () => ({
                    code,
                    fallback: Boolean(this.fallbackParser),
                }));
                if (this.fallbackParser) {
                    parseBarcode = this.fallbackParser.parse_barcode(code);
                } else {
                    this.showGS1IncompatibleBarcodeWarning();
                    endScan({ code, gs1Incompatible: true });
                    return;
                }
            } else {
                endScan({ code, error: error?.message });
                throw error;
            }
        }
        if (Array.isArray(parseBarcode)) {
            log.logic("scan: gs1 dispatch", () => ({
                code,
                elements: parseBarcode.map((e) => e.type),
                handlers: cbMaps.filter((cb) => cb.gs1).length,
            }));
            // A failed callback must not release the scan mutex while another
            // callback is still processing this barcode.
            const results = await Promise.allSettled(
                cbMaps.map(async (cb) => cb.gs1?.(parseBarcode)),
            );
            const failure = results.find((result) => result.status === "rejected");
            if (failure) {
                endScan({ code, error: failure.reason?.message });
                throw failure.reason;
            }
        } else {
            const cbs = cbMaps.map((cbMap) => cbMap[parseBarcode.type]).filter(Boolean);
            log.logic("scan: dispatch", () => ({
                code,
                type: parseBarcode.type,
                baseCode: parseBarcode.base_code,
                value: parseBarcode.value,
                handlers: cbs.length,
                exclusive: Boolean(this.exclusiveCbMap),
            }));
            if (cbs.length === 0) {
                this.showNotFoundNotification(parseBarcode);
            }
            for (const cb of cbs) {
                await cb(parseBarcode);
            }
        }
        endScan({
            code,
            type: Array.isArray(parseBarcode) ? "gs1" : parseBarcode.type,
        });
    }
    showNotFoundNotification(code) {
        this.notification.add(
            _t(
                "The Point of Sale could not find any product, customer, employee or action associated with the scanned barcode.",
            ),
            {
                type: "warning",
                title: _t(`Unknown Barcode`) + " " + this.codeRepr(code),
            },
        );
    }

    codeRepr(parsedBarcode) {
        if (parsedBarcode.code.length > 32) {
            return parsedBarcode.code.substring(0, 29) + "...";
        } else {
            return parsedBarcode.code;
        }
    }

    showGS1IncompatibleBarcodeWarning() {
        this.notification.add(
            _t(
                "This barcode is not compatible with the GS1 standard. Consider configuring a fallback barcode parser from the PoS settings.",
            ),
            {
                type: "warning",
                title: _t("Unsupported Barcode Format"),
            },
        );
    }

    connectToProxy() {
        this.remoteScanning = true;
        log.lifecycle("connectToProxy", () => ({
            alreadyActive: this.remoteActive >= 1,
        }));
        if (this.remoteActive >= 1) {
            return;
        }
        this.remoteActive = 1;
        this.waitForBarcode();
    }

    async waitForBarcode() {
        while (this.remoteScanning) {
            let barcode;
            try {
                barcode = await this.hardwareProxy.message("scanner");
            } catch {
                await new Promise((resolve) => setTimeout(resolve, 1000));
                continue;
            }
            if (!this.remoteScanning) {
                break;
            }
            if (barcode) {
                log.pipeline("[proxy] barcode received", () => ({ barcode }));
                await this.scan(barcode).catch(() => {});
            }
        }
        this.remoteActive = 0;
        log.lifecycle("waitForBarcode: loop ended");
    }

    disconnectFromProxy() {
        log.lifecycle("disconnectFromProxy", () => ({
            wasScanning: this.remoteScanning,
        }));
        this.remoteScanning = false;
    }
}

export const barcodeReaderService = {
    dependencies: [...BarcodeReader.serviceDependencies, "barcode"],
    async start(env, deps) {
        const { dialog, barcode, orm } = deps;
        let barcodeReader = null;
        const endStart = log.perf("service start");

        try {
            if (session.nomenclature_id) {
                const nomenclature = await BarcodeParser.fetchNomenclature(
                    orm,
                    session.nomenclature_id,
                );
                const parser = new BarcodeParser({ nomenclature });
                barcodeReader = new BarcodeReader(parser, deps);
            }

            if (session.fallback_nomenclature_id && barcodeReader) {
                const fallbackNomenclature = await BarcodeParser.fetchNomenclature(
                    orm,
                    session.fallback_nomenclature_id,
                );
                barcodeReader.fallbackParser = new BarcodeParser({
                    nomenclature: fallbackNomenclature,
                });
            }
        } catch (error) {
            logPosMessage(
                "BarcodeReaderService",
                "start",
                "Failed to start barcode reader",
                false,
                [error],
            );
        }
        endStart({
            nomenclature: session.nomenclature_id,
            fallback: session.fallback_nomenclature_id,
            ready: Boolean(barcodeReader),
        });

        barcode.bus.addEventListener("barcode_scanned", (ev) => {
            log.pipeline("[bus] barcode_scanned", () => ({
                barcode: ev.detail.barcode,
                ready: Boolean(barcodeReader),
            }));
            if (barcodeReader) {
                barcodeReader.scan(ev.detail.barcode);
            } else if (session.nomenclature_id) {
                dialog.add(AlertDialog, {
                    title: _t("Unable to parse barcode"),
                    body: _t(
                        "The barcode nomenclature could not be loaded when the session started. Check the connection and reload the Point of Sale to scan barcodes.",
                    ),
                });
            } else {
                dialog.add(AlertDialog, {
                    title: _t("Unable to parse barcode"),
                    body: _t(
                        "No barcode nomenclature has been configured. This can be changed in the configuration settings.",
                    ),
                });
            }
        });

        return barcodeReader;
    },
};

registry.category("services").add("barcode_reader", barcodeReaderService);
