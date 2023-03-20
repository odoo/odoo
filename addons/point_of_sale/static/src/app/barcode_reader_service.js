/** @odoo-module */

import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { ErrorBarcodePopup } from "@point_of_sale/js/Popups/ErrorBarcodePopup";
import BarcodeParser from "barcodes.BarcodeParser";

export class BarcodeReader {
    constructor({ parser, popup }) {
        this.parser = parser;
        this.popup = popup;
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

        let parsedResult = this.parser.parse_barcode(code);
        if (!Array.isArray(parsedResult)) {
            parsedResult = [parsedResult];
        }

        for (const parseBarcode of parsedResult) {
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
    connectToProxy(hwProxy) {
        this.remoteScanning = true;
        if (this.remoteActive >= 1) {
            return;
        }
        this.remoteActive = 1;
        this.waitForBarcode(hwProxy);
    }

    async waitForBarcode(hwProxy) {
        try {
            const barcode = await hwProxy.connection.rpc(
                "/hw_proxy/scanner",
                {},
                { shadow: true, timeout: 7500 }
            );
            if (!this.remoteScanning) {
                this.remoteActive = 0;
                return;
            }
            this.scan(barcode);
        } catch {
            if (!this.remoteScanning) {
                this.remoteActive = 0;
                return;
            }
        }
        this.waitForBarcode();
    }

    // the barcode scanner will stop listening on the hw_proxy/scanner remote interface
    disconnectFromProxy() {
        this.remoteScanning = false;
    }
}

export const barcodeReader = {
    dependencies: ["barcode", "popup"],
    async start(env, { barcode, popup }) {
        let barcodeReader = null;

        if (session.nomenclature_id) {
            const parser = new BarcodeParser({ nomenclature_id: [session.nomenclature_id] });
            await parser.is_loaded();
            barcodeReader = new BarcodeReader({ parser, popup });
        }

        barcode.bus.addEventListener("barcode_scanned", (ev) => {
            if (barcodeReader) {
                barcodeReader.scan(ev.detail.barcode);
            } else {
                popup.add(ErrorPopup, {
                    title: env._t("Unable to parse barcode"),
                    body: env._t(
                        "No barcode nomenclature has been configured. This can be changed in the configuration settings."
                    ),
                });
            }
        });

        return barcodeReader;
    },
};

registry.category("services").add("barcode_reader", barcodeReader);
