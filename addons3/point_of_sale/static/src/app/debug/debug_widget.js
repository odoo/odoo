/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";
import { Transition } from "@web/core/transition";
import { constrain, getLimits, useMovable } from "@point_of_sale/app/utils/movable_hook";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { OrderImportPopup } from "@point_of_sale/app/debug/order_import_popup/order_import_popup";
import { useBus, useService } from "@web/core/utils/hooks";

import { useEffect, useRef, useState, Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { serializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;

export class DebugWidget extends Component {
    static components = { Transition };
    static template = "point_of_sale.DebugWidget";
    static props = { state: { type: Object, shape: { showWidget: Boolean } } };
    setup() {
        this.pos = usePos();
        this.debug = useService("debug");
        this.popup = useService("popup");
        this.barcodeReader = useService("barcode_reader");
        this.hardwareProxy = useService("hardware_proxy");
        const numberBuffer = useService("number_buffer");
        useBus(numberBuffer, "buffer-update", this._onBufferUpdate);
        this.state = useState({
            barcodeInput: "",
            weightInput: "",
            isPaidOrdersReady: false,
            isUnpaidOrdersReady: false,
            buffer: numberBuffer.get(),
        });
        this.root = useRef("root");
        this.position = useState({ left: null, top: null });
        useEffect(
            (root) => {
                this.position.left = root?.offsetLeft;
                this.position.top = root?.offsetTop;
            },
            () => [this.root.el]
        );
        let posBeforeMove;
        useMovable({
            ref: this.root,
            onMoveStart: () => {
                posBeforeMove = { ...this.position };
            },
            onMove: ({ dx, dy }) => {
                const { minX, minY, maxX, maxY } = getLimits(this.root.el, document.body);
                this.position.left = constrain(posBeforeMove.left + dx, minX, maxX);
                this.position.top = constrain(posBeforeMove.top + dy, minY, maxY);
            },
        });

        // Make the background of the "hardware events" section flash when a corresponding message
        // is sent to the proxy.
        for (const eventName of ["open_cashbox", "print_receipt", "scale_read"]) {
            const ref = useRef(eventName);
            let animation;
            useBus(this.hardwareProxy, `send_message:${eventName}`, () => {
                animation?.cancel();
                animation = ref.el?.animate({ backgroundColor: ["#6CD11D", "#1E1E1E"] }, 2000);
            });
        }
    }
    toggleWidget() {
        this.state.isShown = !this.state.isShown;
    }
    setWeight() {
        var weightInKg = parseFloat(this.state.weightInput);
        if (!isNaN(weightInKg)) {
            this.hardwareProxy.setDebugWeight(weightInKg);
        }
    }
    resetWeight() {
        this.state.weightInput = "";
        this.hardwareProxy.resetDebugWeight();
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
    async deleteOrders() {
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: _t("Delete Paid Orders?"),
            body: _t(
                "This operation will permanently destroy all paid orders from the local storage. You will lose all the data. This operation cannot be undone."
            ),
        });
        if (confirmed) {
            this.pos.db.remove_all_orders();
            this.pos.set_synch("connected", 0);
        }
    }
    async deleteUnpaidOrders() {
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: _t("Delete Unpaid Orders?"),
            body: _t(
                "This operation will destroy all unpaid orders in the browser. You will lose all the unsaved data and exit the point of sale. This operation cannot be undone."
            ),
        });
        if (confirmed) {
            this.pos.db.remove_all_unpaid_orders();
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
            this.paidOrdersBlob = this._createBlob(this.pos.export_paid_orders());
            this.state.isPaidOrdersReady = true;
        } catch (error) {
            console.warn(error);
        }
    }
    get paidOrdersFilename() {
        return `${_t("paid orders")} ${serializeDateTime(DateTime.now()).replace(
            /:|\s/gi,
            "-"
        )}.json`;
    }
    get paidOrdersURL() {
        var URL = window.URL || window.webkitURL;
        return URL.createObjectURL(this.paidOrdersBlob);
    }
    // FIXME POSREF why is this two steps?
    prepareUnpaidOrders() {
        try {
            this.unpaidOrdersBlob = this._createBlob(this.pos.export_unpaid_orders());
            this.state.isUnpaidOrdersReady = true;
        } catch (error) {
            console.warn(error);
        }
    }
    get unpaidOrdersFilename() {
        return `${_t("unpaid orders")} ${serializeDateTime(DateTime.now()).replace(
            /:|\s/gi,
            "-"
        )}.json`;
    }
    get unpaidOrdersURL() {
        var URL = window.URL || window.webkitURL;
        return URL.createObjectURL(this.unpaidOrdersBlob);
    }
    async importOrders(event) {
        const file = event.target.files[0];
        if (file) {
            const report = this.pos.import_orders(await file.text());
            await this.popup.add(OrderImportPopup, { report });
        }
    }
    refreshDisplay() {
        this.hardwareProxy.message("display_refresh", {});
    }
    _onBufferUpdate({ detail: value }) {
        this.state.buffer = value;
    }
    get bufferRepr() {
        return `"${this.state.buffer}"`;
    }
    get style() {
        const { left, top } = this.position;
        return top === null ? "" : `position: absolute; left: ${left}px; top: ${top}px;`;
    }
}
