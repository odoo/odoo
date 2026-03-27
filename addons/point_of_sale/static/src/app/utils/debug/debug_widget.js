import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRef, useState, Component, onMounted, onWillDestroy, useEffect } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { serializeDateTime } from "@web/core/l10n/dates";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { downloadPosLogs } from "../pretty_console_log";
const { DateTime } = luxon;

export class DebugWidget extends Component {
    static template = "point_of_sale.DebugWidget";
    static props = {};

    setup() {
        this.pos = usePos();
        this.barcodeReader = useService("barcode_reader");
        this.hardwareProxy = useService("hardware_proxy");
        this.notification = useService("notification");
        this.numberBuffer = useService("number_buffer");
        this.dialog = useService("dialog");
        this.importOrderInput = useRef("import-order-input");
        this.state = useState({
            isOpen: false,
            barcodeInput: "",
            weightInput: "",
            buffer: this.numberBuffer.get(),
            device_identifier: this.pos.device.data.device_identifier,
            next_number: this.pos.device.data.next_number,
            unsynced_number_stack: JSON.stringify(
                this.pos.device?.data?.unsynced_number_stack || []
            ),
        });

        useBus(this.numberBuffer, "buffer-update", this._onBufferUpdate);
        onMounted(() => {
            if (!this.importOrderInput || !this.importOrderInput.el) {
                return;
            }

            this.importOrderInput.el.addEventListener("click", this.handleFileOrderImport);
        });
        onWillDestroy(() => {
            if (this.importOrderInput?.el) {
                this.importOrderInput.el.removeEventListener("click", this.handleFileOrderImport);
            }
        });

        useEffect(
            (isOpen) => {
                if (!isOpen) {
                    return;
                }

                // Since addEventListener('storage') is not triggered from the same tab,
                // we need to poll the device data to keep the widget updated.
                const interval = setInterval(() => {
                    this.state.next_number = this.pos.device?.data?.next_number;
                    this.state.unsynced_number_stack = JSON.stringify(
                        this.pos.device?.data?.unsynced_number_stack || []
                    );
                }, 500);

                return () => clearInterval(interval);
            },
            () => [this.state.isOpen]
        );
    }
    get isDisabled() {
        return this.pos.cashier._role === "minimal";
    }
    disableDebugMode() {
        const url = new URL(window.location.href);
        url.searchParams.delete("debug");
        window.history.replaceState({}, document.title, url);
        window.location.reload();
    }
    handleFileOrderImport() {
        document.getElementById("import-order-input").click();
    }
    toggleWidget() {
        this.state.isOpen = !this.state.isOpen;
    }
    async barcodeScan() {
        if (!this.barcodeReader) {
            return;
        }
        await this.barcodeReader.scan(this.state.barcodeInput);
    }
    async barcodeScanEAN() {
        if (!this.barcodeReader) {
            return;
        }
        const ean = this.barcodeReader.parser.sanitize_ean(this.state.barcodeInput || "0");
        this.state.barcodeInput = ean;
        await this.barcodeReader.scan(ean);
    }
    _createBlob(contents) {
        if (typeof contents !== "string") {
            contents = JSON.stringify(contents, null, 2);
        }
        return new Blob([contents]);
    }
    deleteOrders({ paid = true } = {}) {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete Orders?"),
            body: _t(
                `This operation will destroy all ${
                    paid ? "paid" : "unpaid"
                } orders in the browser. You will lose all the data. This operation cannot be undone.`
            ),
            confirm: () => {
                this.pos.data.network.unsyncData = [];
                const orders = this.pos.models["pos.order"].filter(
                    (order) => order.finalized === paid
                );

                for (const order of orders) {
                    this.pos.data.localDeleteCascade(order, !paid);
                }

                if (!this.pos.getOrder()) {
                    return this.pos.addNewOrder();
                }
            },
        });
    }

    deleteAllIndexedDB() {
        if (!window.indexedDB || !window.indexedDB.databases) {
            console.warn("IndexedDB is not supported in this browser.");
            return;
        }

        window.indexedDB.databases().then((r) => {
            for (var i = 0; i < r.length; i++) {
                window.indexedDB.deleteDatabase(r[i].name);
            }
        });
    }

    async exportData() {
        const data = await this.pos.data.synchronizeLocalDataInIndexedDB();
        const blob = this._createBlob(data);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const fileName = `pos_data${serializeDateTime(DateTime.now()).replace(/:|\s/gi, "-")}.json`;
        a.href = url;
        a.download = fileName;
        a.click();
    }
    async importData(event) {
        const file = event.target.files[0];
        if (file) {
            try {
                const jsonData = JSON.parse(await file.text());
                await this.pos.data.getLocalDataFromIndexedDB(jsonData);
            } catch (error) {
                console.warn("An error occured during import", error);
            }
        }
    }

    refreshDisplay() {
        this.hardwareProxy.message("display_refresh", {});
    }
    async downloadLogs() {
        await downloadPosLogs();
    }
    _onBufferUpdate({ detail: value }) {
        this.state.buffer = value;
    }
    get bufferRepr() {
        return `"${this.state.buffer}"`;
    }
}
