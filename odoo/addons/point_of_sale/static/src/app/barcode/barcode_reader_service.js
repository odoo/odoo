/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ErrorBarcodePopup } from "@point_of_sale/app/barcode/error_popup/barcode_error_popup";
import { BarcodeParser } from "@barcodes/js/barcode_parser";
import { GS1BarcodeError } from "@barcodes_gs1_nomenclature/js/barcode_parser";

export class BarcodeReader {
    static serviceDependencies = ["popup", "hardware_proxy"];
    constructor(parser, { popup, hardware_proxy }) {
        this.parser = parser;
        this.popup = popup;
        this.hardwareProxy = hardware_proxy;
        this.setup();
    }

    setup() {
        this.mutex = new Mutex();
        this.cbMaps = new Set();
        // FIXME POSREF: When LoginScreen becomes a normal screen, we can remove this exclusive callback handling.
        this.exclusiveCbMap = null;
        this.remoteScanning = false;
        this.remoteActive = 0;
    }

    register(cbMap, exclusive) {
        if (exclusive) {
            this.exclusiveCbMap = cbMap;
        } else {
            this.cbMaps.add(cbMap);
        }
        return () => {
            if (exclusive) {
                this.exclusiveCbMap = null;
            } else {
                this.cbMaps.delete(cbMap);
            }
        };
    }

    scan(code) {
        return this.mutex.exec(() => this._scan(code));
    }

    async _scan(code) {
        if (!code) {
            return;
        }

        const cbMaps = this.exclusiveCbMap ? [this.exclusiveCbMap] : [...this.cbMaps];

        let parseBarcode;
        try {
            parseBarcode = this.parser.parse_barcode(code);
            if (Array.isArray(parseBarcode) && !parseBarcode.some(element => element.type === 'product')) {
                throw new GS1BarcodeError('The GS1 barcode must contain a product.');
            }
        } catch (error) {
            if (this.fallbackParser && error instanceof GS1BarcodeError) {
                parseBarcode = this.fallbackParser.parse_barcode(code);
            } else {
                throw error;
            }
        }
        if (Array.isArray(parseBarcode)) {
            cbMaps.map((cb) => cb.gs1?.(parseBarcode));
        } else {
            const cbs = cbMaps.map((cbMap) => cbMap[parseBarcode.type]).filter(Boolean);
            if (cbs.length === 0) {
                this.popup.add(ErrorBarcodePopup, { code: this.codeRepr(parseBarcode) });
            }
            for (const cb of cbs) {
                await cb(parseBarcode);
            }
        }
    }

    codeRepr(parsedBarcode) {
        if (parsedBarcode.code.length > 32) {
            return parsedBarcode.code.substring(0, 29) + "...";
        } else {
            return parsedBarcode.code;
        }
    }

    // the barcode scanner will listen on the hw_proxy/scanner interface for
    // scan events until disconnectFromProxy is called
    connectToProxy() {
        this.remoteScanning = true;
        if (this.remoteActive >= 1) {
            return;
        }
        this.remoteActive = 1;
        this.waitForBarcode();
    }

    async waitForBarcode() {
        const barcode = await this.hardwareProxy.message("scanner").catch(() => {});
        if (!this.remoteScanning) {
            this.remoteActive = 0;
            return;
        }
        this.scan(barcode);
        this.waitForBarcode();
    }

    // the barcode scanner will stop listening on the hw_proxy/scanner remote interface
    disconnectFromProxy() {
        this.remoteScanning = false;
    }
}

export const barcodeReaderService = {
    dependencies: [...BarcodeReader.serviceDependencies, "popup", "barcode", "orm"],
    async start(env, deps) {
        const { popup, barcode, orm } = deps;
        let barcodeReader = null;

        if (session.nomenclature_id) {
            const nomenclature = await BarcodeParser.fetchNomenclature(
                orm,
                session.nomenclature_id
            );
            const parser = new BarcodeParser({ nomenclature });
            barcodeReader = new BarcodeReader(parser, deps);
        }

        if (session.fallback_nomenclature_id && barcodeReader) {
            const fallbackNomenclature = await BarcodeParser.fetchNomenclature(
                orm,
                session.fallback_nomenclature_id
            );
            barcodeReader.fallbackParser = new BarcodeParser({
                nomenclature: fallbackNomenclature,
            });
        }

        barcode.bus.addEventListener("barcode_scanned", (ev) => {
            if (barcodeReader) {
                barcodeReader.scan(ev.detail.barcode);
            } else {
                popup.add(ErrorPopup, {
                    title: _t("Unable to parse barcode"),
                    body: _t(
                        "No barcode nomenclature has been configured. This can be changed in the configuration settings."
                    ),
                });
            }
        });

        return barcodeReader;
    },
};

registry.category("services").add("barcode_reader", barcodeReaderService);
