/** @odoo-module */

import { parse } from "web.field_utils";
import { numberBuffer } from "@point_of_sale/js/Misc/NumberBuffer";
import { PosComponent } from "@point_of_sale/js/PosComponent";
import { usePos } from "@point_of_sale/app/pos_store";
import { registry } from "@web/core/registry";
import { Transition } from "@web/core/transition";
import { Draggable } from "@point_of_sale/js/Misc/Draggable";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";
import { OrderImportPopup } from "@point_of_sale/js/Popups/OrderImportPopup";

const { onMounted, onWillUnmount, useRef, useState } = owl;

export class DebugWidget extends PosComponent {
    static components = { Transition, Draggable };
    static template = "point_of_sale.DebugWidget";
    setup() {
        super.setup();
        this.pos = usePos();
        this.state = useState({
            barcodeInput: "",
            weightInput: "",
            isPaidOrdersReady: false,
            isUnpaidOrdersReady: false,
            buffer: numberBuffer.get(),
        });

        // NOTE: Perhaps this can still be improved.
        // What we do here is loop thru the `event` elements
        // then we assign animation that happens when the event is triggered
        // in the proxy. E.g. if open_cashbox is sent, the open_cashbox element
        // changes color from '#6CD11D' to '#1E1E1E' for a duration of 2sec.
        this.eventElementsRef = {};
        this.animations = {};
        for (const eventName of ["open_cashbox", "print_receipt", "scale_read"]) {
            this.eventElementsRef[eventName] = useRef(eventName);
            this.env.proxy.add_notification(
                eventName,
                (() => {
                    if (this.animations[eventName]) {
                        this.animations[eventName].cancel();
                    }
                    const eventElement = this.eventElementsRef[eventName].el;
                    eventElement.style.backgroundColor = "#6CD11D";
                    this.animations[eventName] = eventElement.animate(
                        { backgroundColor: ["#6CD11D", "#1E1E1E"] },
                        2000
                    );
                }).bind(this)
            );
        }

        onMounted(() => {
            numberBuffer.on("buffer-update", this, this._onBufferUpdate);
        });

        onWillUnmount(() => {
            numberBuffer.off("buffer-update", this, this._onBufferUpdate);
        });
    }
    toggleWidget() {
        this.state.isShown = !this.state.isShown;
    }
    setWeight() {
        var weightInKg = parse.float(this.state.weightInput);
        if (!isNaN(weightInKg)) {
            this.env.proxy.debug_set_weight(weightInKg);
        }
    }
    resetWeight() {
        this.state.weightInput = "";
        this.env.proxy.debug_reset_weight();
    }
    async barcodeScan() {
        await this.env.barcode_reader.scan(this.state.barcodeInput);
    }
    async barcodeScanEAN() {
        const ean = this.env.barcode_reader.barcode_parser.sanitize_ean(
            this.state.barcodeInput || "0"
        );
        this.state.barcodeInput = ean;
        await this.env.barcode_reader.scan(ean);
    }
    async deleteOrders() {
        const { confirmed } = await this.showPopup(ConfirmPopup, {
            title: this.env._t("Delete Paid Orders ?"),
            body: this.env._t(
                "This operation will permanently destroy all paid orders from the local storage. You will lose all the data. This operation cannot be undone."
            ),
        });
        if (confirmed) {
            this.env.pos.db.remove_all_orders();
            this.env.pos.set_synch("connected", 0);
        }
    }
    async deleteUnpaidOrders() {
        const { confirmed } = await this.showPopup(ConfirmPopup, {
            title: this.env._t("Delete Unpaid Orders ?"),
            body: this.env._t(
                "This operation will destroy all unpaid orders in the browser. You will lose all the unsaved data and exit the point of sale. This operation cannot be undone."
            ),
        });
        if (confirmed) {
            this.env.pos.db.remove_all_unpaid_orders();
            window.location = "/";
        }
    }
    _createBlob(contents) {
        if (typeof contents !== "string") {
            contents = JSON.stringify(contents, null, 2);
        }
        return new Blob([contents]);
    }
    // IMPROVEMENT: Duplicated codes for downloading paid and unpaid orders.
    // The implementation can be better.
    preparePaidOrders() {
        try {
            this.paidOrdersBlob = this._createBlob(this.env.pos.export_paid_orders());
            this.state.isPaidOrdersReady = true;
        } catch (error) {
            console.warn(error);
        }
    }
    get paidOrdersFilename() {
        return `${this.env._t("paid orders")} ${moment().format("YYYY-MM-DD-HH-mm-ss")}.json`;
    }
    get paidOrdersURL() {
        var URL = window.URL || window.webkitURL;
        return URL.createObjectURL(this.paidOrdersBlob);
    }
    // FIXME POSREF why is this two steps?
    prepareUnpaidOrders() {
        try {
            this.unpaidOrdersBlob = this._createBlob(this.env.pos.export_unpaid_orders());
            this.state.isUnpaidOrdersReady = true;
        } catch (error) {
            console.warn(error);
        }
    }
    get unpaidOrdersFilename() {
        return `${this.env._t("unpaid orders")} ${moment().format("YYYY-MM-DD-HH-mm-ss")}.json`;
    }
    get unpaidOrdersURL() {
        var URL = window.URL || window.webkitURL;
        return URL.createObjectURL(this.unpaidOrdersBlob);
    }
    async importOrders(event) {
        const file = event.target.files[0];
        if (file) {
            const report = this.env.pos.import_orders(await file.text());
            await this.showPopup(OrderImportPopup, { report });
        }
    }
    refreshDisplay() {
        this.env.proxy.message("display_refresh", {});
    }
    _onBufferUpdate(buffer) {
        this.state.buffer = buffer;
    }
    get bufferRepr() {
        return `"${this.state.buffer}"`;
    }
}

registry.category("main_components").add("DebugWidget", { Component: DebugWidget });
