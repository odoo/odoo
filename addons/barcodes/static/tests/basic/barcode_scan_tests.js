/** @odoo-module **/

import { BarcodeScanner } from "@barcodes/components/barcode_scanner";
import { getFixture, mount } from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";

import { xml, Component } from "@odoo/owl";

QUnit.module("Barcode scan", {});

QUnit.test("Display notification for media device permission on barcode scanning", async () => {
    navigator.mediaDevices.getUserMedia = function() {
        return Promise.reject(new DOMException("", "NotAllowedError"));
    };

    class BarcodeScan extends Component {
        static template = xml`
            <div>
                <BarcodeScanner onBarcodeScanned="(ev) => this.onBarcodeScanned(ev)"/>
            </div>
        `;
        static components = { BarcodeScanner };
        static props = ["*"];
    }

    const target = getFixture();
    const { env } = await createWebClient({});
    await mount(BarcodeScan, target, { env });

    await document.querySelector('.o_mobile_barcode').click();
    await contains(".modal-body", { text: "Unable to access cameraCould not start scanning. Odoo needs your authorization first." });
    await document.querySelector('.modal-header button[aria-label="Close"]').click();
})
